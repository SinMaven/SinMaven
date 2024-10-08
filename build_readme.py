import feedparser
import requests
import pathlib
import re

# Set the root directory for the script
root = pathlib.Path(__file__).parent.resolve()

def replace_chunk(content, marker, chunk, inline=True):
    """Replace a specified chunk in the content between markers with a new chunk."""
    r = re.compile(
        r"<!-- {} starts -->.*<!-- {} ends -->".format(marker, marker),
        re.DOTALL,
    )
    if not inline:
        chunk = "\n{}".format(chunk)
    chunk = "<!-- {} starts -->\n{}\n<!-- {} ends -->".format(marker, chunk, marker)
    return r.sub(chunk, content)

def get_tils():
    """Fetch the latest TIL entries from the specified README."""
    til_readme_url = "https://raw.githubusercontent.com/SinMaven/TIL/master/README.md"
    response = requests.get(til_readme_url)
    response.raise_for_status()  # Ensure the request was successful

    all_text = response.text
    search_re = re.findall(r'(\*+).(\[.*?\])(\(.*?\)).?-(.+)', all_text, re.M | re.I)
    dt_til = sorted(search_re, key=lambda search_re: search_re[3], reverse=True)[:3]

    print('~' * 50)
    print('Latest TIL entries (up to 3):', dt_til)
    print('~' * 50)

    til_md = "\n".join(f"{i[0]} {i[1]}{i[2]}" for i in dt_til)
    
    print('~' * 50)
    print('Formatted TIL entries:', til_md)
    print('~' * 50)

    return til_md

def fetch_blog_entries():
    """Fetch the latest blog entries from the RSS feed."""
    entries = feedparser.parse("https://SinMaven.github.io/rss.xml")["entries"]
    return [
        {
            "title": entry["title"],
            "url": entry["link"].split("#")[0],
            "published": entry["published"].split("T")[0],
        }
        for entry in entries
    ]

if __name__ == "__main__":
    readme_path = root / "README.md"
    
    # Read the current content of the README
    with open(readme_path, "r") as file:
        readme_contents = file.read()

    # Fetch and format the latest blog entries
    entries = fetch_blog_entries()[:3]
    entries_md = "<br>".join(
        [f"• [{entry['title']}]({entry['url']})" for entry in entries]
    )

    # Ensure a single new line before inserting blog posts
    entries_md = "\n" + entries_md  # Add a new line before blog posts

    # Replace the blog section in the README
    rewritten = replace_chunk(readme_contents, "blog", entries_md)

    # Fetch and format the latest TIL entries
    til_readme_contents = get_tils()

    print('~' * 50)
    print('TIL README contents:', til_readme_contents)
    print('~' * 50)

    # Replace the TIL entries in the README
    rewritten = replace_chunk(rewritten, "tilentries", til_readme_contents)

    print('~' * 50)
    print('Rewritten content after updating TILs:', rewritten)
    print('~' * 50)

    # Write the updated content back to the README
    with open(readme_path, "w") as file:
        file.write(rewritten)
