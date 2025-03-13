import requests
import re
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Define the markers for the joke section
START_COMMENT = "<!-- JOKE:START -->"
END_COMMENT = "<!-- JOKE:END -->"
# Updated regex to capture content between markers
joke_reg = re.compile(f"({START_COMMENT})([\\s\\S]+)({END_COMMENT})")

def main():
    logger.info("Starting daily joke script")
    
    try:
        # Fetch joke from API
        logger.info("Fetching joke from API")
        response = requests.get("https://v2.jokeapi.dev/joke/Programming?blacklistFlags=nsfw,religious,political,racist,sexist,explicit&type=twopart")
        
        if response.status_code == 200:
            data = response.json()
            question = data["setup"]
            punchline = data["delivery"]
            
            logger.info(f"Joke fetched successfully: {question}")
            
            # Format the joke in markdown with Q: and A: format
            joke_content = f"""
**Q:** {question}

**A:** {punchline}
"""
            
            print(f"{START_COMMENT}{joke_content}{END_COMMENT}")
            
            # Read the current README
            logger.info("Reading README.md file")
            try:
                with open('README.md', 'r', encoding='utf-8') as file:
                    readme_content = file.read()
                logger.info("Successfully read README.md")
            except FileNotFoundError:
                logger.error("README.md file not found")
                raise
            
            # Check for existing joke section
            match = joke_reg.search(readme_content)
            if match:
                logger.info("Found existing joke section")
                
                # Replace only the content between markers, preserving the markers
                new_readme = joke_reg.sub(r'\1' + joke_content + r'\3', readme_content)
                logger.info("Replaced existing joke content with new one")
            else:
                logger.warning("No existing joke section found in README")
                # If no joke section exists, this shouldn't happen based on your README template
                # But just in case, we'll append it
                new_readme = readme_content
                logger.info("Using existing README content")
            
            # Write the updated README
            logger.info("Writing updated README.md")
            with open('README.md', 'w', encoding='utf-8') as file:
                file.write(new_readme)
            
            logger.info('Successfully updated README with daily joke!')
        else:
            logger.error(f'Error fetching joke: {response.status_code}')
            logger.error(f'Response: {response.text}')
    except Exception as e:
        logger.error(f"Error in main function: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        main()
        logger.info("Script completed successfully")
    except Exception as e:
        logger.error(f"Script failed with error: {e}")
        raise
