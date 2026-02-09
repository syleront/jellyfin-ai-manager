import xml.etree.ElementTree as ET
from xml.dom import minidom
import logging

logger = logging.getLogger(__name__)

def _save_pretty_xml(root, output_path):
    xml_str = ET.tostring(root, encoding='utf-8')
    reparsed = minidom.parseString(xml_str)
    pretty_xml = reparsed.toprettyxml(indent="  ")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(pretty_xml)
        logger.info(f"Successfully created .nfo: {output_path}")
    except Exception as e:
        logger.error(f"Failed to write .nfo file {output_path}: {e}")

def generate_movie_nfo(movie_data: dict, output_path: str):
    """Generates a Jellyfin-compatible .nfo file for a movie."""
    movie = ET.Element("movie")
    ET.SubElement(movie, "title").text = movie_data.get("title", "")
    ET.SubElement(movie, "originaltitle").text = movie_data.get("original_title", "")
    
    release_date = movie_data.get("release_date", "")
    if release_date:
        ET.SubElement(movie, "year").text = release_date.split("-")[0]
        ET.SubElement(movie, "premiered").text = release_date
    
    ET.SubElement(movie, "rating").text = str(movie_data.get("vote_average", ""))
    ET.SubElement(movie, "plot").text = movie_data.get("overview", "")
    ET.SubElement(movie, "runtime").text = str(movie_data.get("runtime", ""))
    
    for genre in movie_data.get("genres", []):
        ET.SubElement(movie, "genre").text = genre.get("name")
    
    for studio in movie_data.get("production_companies", []):
        ET.SubElement(movie, "studio").text = studio.get("name")

    ET.SubElement(movie, "tmdbid").text = str(movie_data.get("id", ""))
    
    uniqueid_tmdb = ET.SubElement(movie, "uniqueid")
    uniqueid_tmdb.set("type", "tmdb")
    uniqueid_tmdb.set("default", "true")
    uniqueid_tmdb.text = str(movie_data.get("id", ""))

    credits = movie_data.get("credits", {})
    for person in credits.get("crew", []):
        if person.get("job") == "Director":
            ET.SubElement(movie, "director").text = person.get("name")
        elif person.get("job") in ["Writer", "Screenplay"]:
            ET.SubElement(movie, "writer").text = person.get("name")

    for actor in credits.get("cast", [])[:15]:
        actor_elem = ET.SubElement(movie, "actor")
        ET.SubElement(actor_elem, "name").text = actor.get("name")
        ET.SubElement(actor_elem, "role").text = actor.get("character")
        if actor.get("profile_path"):
            ET.SubElement(actor_elem, "thumb").text = f"https://image.tmdb.org/t/p/original{actor.get('profile_path')}"

    if movie_data.get("poster_path"):
        ET.SubElement(movie, "thumb").text = f"https://image.tmdb.org/t/p/original{movie_data.get('poster_path')}"

    _save_pretty_xml(movie, output_path)

def generate_series_nfo(series_data: dict, output_path: str):
    """Generates a tvshow.nfo file for a TV series."""
    tvshow = ET.Element("tvshow")
    ET.SubElement(tvshow, "title").text = series_data.get("name", "")
    ET.SubElement(tvshow, "originaltitle").text = series_data.get("original_name", "")
    
    first_air_date = series_data.get("first_air_date", "")
    if first_air_date:
        ET.SubElement(tvshow, "year").text = first_air_date.split("-")[0]
        ET.SubElement(tvshow, "premiered").text = first_air_date
    
    ET.SubElement(tvshow, "rating").text = str(series_data.get("vote_average", ""))
    ET.SubElement(tvshow, "plot").text = series_data.get("overview", "")
    
    for genre in series_data.get("genres", []):
        ET.SubElement(tvshow, "genre").text = genre.get("name")

    ET.SubElement(tvshow, "tmdbid").text = str(series_data.get("id", ""))
    
    uniqueid_tmdb = ET.SubElement(tvshow, "uniqueid")
    uniqueid_tmdb.set("type", "tmdb")
    uniqueid_tmdb.set("default", "true")
    uniqueid_tmdb.text = str(series_data.get("id", ""))

    _save_pretty_xml(tvshow, output_path)

def generate_episode_nfo(episode_data: dict, output_path: str):
    """Generates an .nfo file for a specific episode."""
    episodedetails = ET.Element("episodedetails")
    ET.SubElement(episodedetails, "title").text = episode_data.get("name", "")
    ET.SubElement(episodedetails, "plot").text = episode_data.get("overview", "")
    ET.SubElement(episodedetails, "season").text = str(episode_data.get("season_number", ""))
    ET.SubElement(episodedetails, "episode").text = str(episode_data.get("episode_number", ""))
    
    air_date = episode_data.get("air_date", "")
    if air_date:
        ET.SubElement(episodedetails, "aired").text = air_date

    ET.SubElement(episodedetails, "tmdbid").text = str(episode_data.get("id", ""))
    
    uniqueid_tmdb = ET.SubElement(episodedetails, "uniqueid")
    uniqueid_tmdb.set("type", "tmdb")
    uniqueid_tmdb.set("default", "true")
    uniqueid_tmdb.text = str(episode_data.get("id", ""))

    _save_pretty_xml(episodedetails, output_path)
