import logging
import json
from openai import OpenAI

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, api_key: str, model: str, base_url: str):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model

    def extract_media_info_batch(self, filenames: list[str], folder_context: str = None, existing_series_folders: list[str] = None):
        """
        Uses LLM to extract media info for a batch of filenames from the same folder.
        Returns a list of dictionaries with the extracted info, matching the input order.
        """
        if not filenames:
            return []

        filenames_str = "\n".join([f"{i+1}. {f}" for i, f in enumerate(filenames)])
        
        context_parts = []
        if folder_context:
            context_parts.append(f"Folder context: {folder_context}")
        if existing_series_folders:
            folders_str = "\n".join([f"- {f}" for f in existing_series_folders])
            context_parts.append(f"Existing series folders:\n{folders_str}")
        context_str = "\n".join(context_parts) + "\n" if context_parts else ""
        
        prompt = f"""Extract media information from the following list of filenames.
These files are from the same folder, so they might share patterns (e.g., same series).
However, the folder might contain a mix of movies and series.

{context_str}
Filenames:
{filenames_str}

For each file, determine if it's a "movie" or a "series".
- If it's a movie, extract "title" and "year".
- If it's a series, extract "title", "year" (of the series start), "season", and "episode".
- For multi-episode files (e.g., E19-20), return "episode" as a string (e.g., "19-20").
- For multi-season files, return "season" as a string.

Search for the title as it appears on themoviedb.org.
Always return the "title" in English, regardless of the origin of the series or film.

If the series matches one of the existing series folders, return the exact "title" and "year" from that folder, so that new episodes are placed into the same existing folder.

Respond ONLY with a JSON array of objects, one for each filename in the exact same order.

Example Output:
[
  {{"type": "movie", "title": "Inception", "year": 2010}},
  {{"type": "series", "title": "Breaking Bad", "year": 2008, "season": 1, "episode": 5}},
  {{"type": "series", "title": "Danny Phantom", "year": 2004, "season": 2, "episode": "19-20"}}
]
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts media metadata from filenames. You always respond with valid JSON array."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "text" }
            )
            
            content = response.choices[0].message.content
            
            # Clean up content if it's wrapped in markdown code blocks
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0].strip()
            elif content.startswith("```"):
                content = content.split("```")[1].split("```")[0].strip()
                
            info_list = json.loads(content)
            if not isinstance(info_list, list):
                logger.error(f"LLM did not return a list for batch: {filenames}")
                return None
            return info_list
        except Exception as e:
            logger.error(f"Error extracting media info for batch: {e}")
            return None
