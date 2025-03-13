# Inspired by https://github.com/swyxio/swyxio
import os
import re
import logging
from github import Github

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

logger.info("Starting endorsement script")

# Check environment variables
missing_vars = []
for var in ["ENV_GITHUB_TOKEN", "CI_REPOSITORY_OWNER", "CI_REPOSITORY_NAME"]:
    if os.environ.get(var) is None:
        missing_vars.append(var)
        logger.error(f"{var} environment variable is not set")

if missing_vars:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Environment variables
REPO_DETAILS = {
    "owner": os.environ.get("CI_REPOSITORY_OWNER"),
    "repo": os.environ.get("CI_REPOSITORY_NAME"),  # Fixed: was using owner instead of name
}
logger.info(f"Repository details: {REPO_DETAILS}")

START_COMMENT = "<!-- ENDORSEMENTS:START -->"
END_COMMENT = "<!-- ENDORSEMENTS:END -->"
list_reg = re.compile(f"{START_COMMENT}[\\s\\S]+{END_COMMENT}")

# Initialize Github client
logger.info("Initializing Github client")
g = Github(os.environ.get("ENV_GITHUB_TOKEN"))


def main():
    try:
        repo_path = f"{REPO_DETAILS['owner']}/{REPO_DETAILS['repo']}"
        logger.info(f"Getting repository: {repo_path}")
        repo = g.get_repo(repo_path)
        
        # Get README
        logger.info("Fetching README content")
        readme = get_readme(repo)
        
        # Check for existing section
        logger.info("Checking for existing endorsements section")
        old_section_match = list_reg.search(readme["content"])
        
        # Get reactions data
        logger.info("Fetching endorsement issues and reactions")
        data = get_reactions(repo)
        logger.info(f"Found {len(data)} endorsement issues")
        
        try:
            # Generate new content (without fences)
            logger.info("Generating new endorsements content")
            new_content = generate_endorsements_content(data)
            
            if old_section_match:
                old_section = old_section_match.group(0)
                # Extract just the content between the fences from the old section
                old_content_match = re.search(f"{START_COMMENT}\n(.*?)\n{END_COMMENT}", old_section, re.DOTALL)
                old_content = old_content_match.group(1) if old_content_match else ""
                
                # Add debug logging to see what's being compared
                logger.info(f"Old content: '{old_content}'")
                logger.info(f"New content: '{new_content}'")
                
                if new_content.strip() == old_content.strip():
                    logger.info('NO CHANGE detected in the endorsements, skipping commit')
                    return
                
                logger.info("Changes detected, updating README")
                
                # Create the new section with the same fence markers
                new_section = f"{START_COMMENT}\n{new_content}\n{END_COMMENT}"
                # Replace old section with new section
                new_contents = readme["content"].replace(old_section, new_section)
            else:
                logger.info("No existing section found, appending to README")
                new_section = f"{START_COMMENT}\n{new_content}\n{END_COMMENT}"
                new_contents = readme["content"] + "\n\n" + new_section
            
            # In local debug mode, update the local README file directly
            logger.info("LOCAL DEBUG MODE: Updating local README.md file")
            logger.info("------- NEW README CONTENT START -------")
            logger.info(new_contents)
            logger.info("------- NEW README CONTENT END -------")
            
            # Write directly to the local README.md file
            with open("README.md", "w", encoding="utf-8") as f:
                f.write(new_contents)
            logger.info("Successfully updated local README.md file")
        except Exception as err:
            logger.error(f"Error updating README: {err}", exc_info=True)
            raise
    except Exception as err:
        logger.error(f"Error in main function: {err}", exc_info=True)
        raise

def generate_endorsements_content(data):
    logger.info("Generating endorsements Markdown")
    rendered_list = []

    logger.info(f"Endorsement data: {data}")
    
    if not data:
        logger.info("No endorsement data found, creating empty list")
        # Even with no data, create a placeholder message
        rendered_list_str = "- No endorsements yet. Be the first to endorse!"
    else:
        for x in data:
            logger.info(f"Processing endorsement title: '{x['title']}'")
            
            # Clean the title - remove HTML tags but preserve emojis
            clean_title = re.sub(r"<style[^>]*>.*</style>", "", x["title"], flags=re.DOTALL)
            clean_title = re.sub(r"<script[^>]*>.*</script>", "", clean_title, flags=re.DOTALL)
            clean_title = re.sub(r"<[^>]+>", "", clean_title)
            clean_title = re.sub(r"([\r\n]+ +)+", "", clean_title)
            
            logger.info(f"Cleaned title: '{clean_title}'")
            
            # Generate reactions as markdown
            reactions_md = ""
            
            # Assert that we have at least one reaction with an avatar
            if not x["reactions"]:
                logger.warning(f"Issue #{x['number']} has no endorsers")
            
            for reaction in x["reactions"]:
                # Assert that each reaction has a user with an avatar URL
                assert "user" in reaction, f"Endorser in issue #{x['number']} is missing user data"
                assert "avatar_url" in reaction["user"], f"User in issue #{x['number']} is missing avatar_url"
                
                # Make sure the avatar URL is properly formatted for Markdown
                avatar_url = reaction["user"]["avatar_url"]
                # Remove any size parameter that might already be in the URL
                avatar_url = re.sub(r"&s=\d+", "", avatar_url)
                # Add size parameter to ensure consistent display
                avatar_url = f"{avatar_url}&s=20"
                
                # Use proper Markdown image syntax with alt text
                user_login = reaction["user"].get("login", "User")
                reactions_md += f'![{user_login}]({avatar_url} "{user_login}") '
            
            # Create list item with markdown
            list_item = f'- [{clean_title}]({x["url"]}): {reactions_md}'
            rendered_list.append(list_item)
        
        rendered_list_str = "\n".join(rendered_list)
    
    return rendered_list_str

def get_readme(repo):
    try:
        # Use local README file instead of fetching from GitHub
        logger.info("Reading local README.md file")
        
        try:
            with open("README.md", "r", encoding="utf-8") as f:
                content = f.read()
                
            logger.info("Successfully read local README.md")
            logger.info(f"README content: \n{content}")
            
            return {
                "content": content,
            }
        except FileNotFoundError:
            logger.error("Local README.md file not found")
            raise
            
    except Exception as e:
        logger.error(f"Error getting README: {e}", exc_info=True)
        raise

def get_reactions(repo):
    try:
        logger.info("Fetching open issues")
        issues = repo.get_issues(state="open")
        
        # Filter issues that start with "Endorse: "
        endorsement_issues = []
        for issue in issues:
            if issue.title.startswith("Endorse: "):
                logger.info(f"Found endorsement issue #{issue.number}: {issue.title}")
                # Keep the entire title after "Endorse: " including emojis
                endorsement_issues.append({
                    "issue": issue,
                    "title": issue.title[9:].strip()  # Remove "Endorse: " prefix and trim whitespace
                })
        
        logger.info(f"Found {len(endorsement_issues)} endorsement issues")
        
        result = []
        for item in endorsement_issues:
            issue = item["issue"]
            
            # Track unique users who have endorsed (to avoid duplicates)
            endorsers = {}
            
            # 1. Add the issue creator as an endorser
            if issue.user and issue.user.avatar_url:
                logger.info(f"Adding issue creator: {issue.user.login} with avatar: {issue.user.avatar_url}")
                endorsers[issue.user.login] = {
                    "avatar_url": issue.user.avatar_url
                }
            
            # 2. Get all comments for the issue and add commenters as endorsers
            logger.info(f"Fetching comments for issue #{issue.number}")
            for comment in issue.get_comments():
                if comment.user and comment.user.avatar_url:
                    logger.info(f"Adding commenter: {comment.user.login} with avatar: {comment.user.avatar_url}")
                    endorsers[comment.user.login] = {
                        "avatar_url": comment.user.avatar_url
                    }
            
            # 3. Get reactions for the issue
            logger.info(f"Fetching reactions for issue #{issue.number}")
            for reaction in issue.get_reactions():
                if reaction.user and reaction.user.avatar_url:
                    logger.info(f"Adding reactor: {reaction.user.login} with avatar: {reaction.user.avatar_url}")
                    endorsers[reaction.user.login] = {
                        "avatar_url": reaction.user.avatar_url
                    }
            
            # Convert the dictionary to a list for the result
            reactions = []
            for login, user_data in endorsers.items():
                reactions.append({
                    "user": {
                        "login": login,
                        "avatar_url": user_data["avatar_url"]
                    }
                })
            
            logger.info(f"Found {len(reactions)} total endorsers for issue #{issue.number}")
            
            # Assert that we have at least one endorser with an avatar
            if not reactions:
                logger.warning(f"Issue #{issue.number} has no valid endorsers with avatars")
                # Add a placeholder message for issues with no endorsers
                reactions.append({
                    "user": {
                        "login": "placeholder",
                        "avatar_url": "https://github.com/identicons/placeholder.png"
                    }
                })
            
            result.append({
                "title": item["title"],
                "url": issue.html_url,
                "number": issue.number,
                "reactions": reactions
            })
        
        return result
    except Exception as e:
        logger.error(f"Error getting reactions: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        logger.info("Starting main function")
        main()
        logger.info("Script completed successfully")
    except Exception as e:
        logger.error(f"Script failed with error: {e}", exc_info=True)
        raise