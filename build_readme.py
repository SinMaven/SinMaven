from python_graphql_client import GraphqlClient
from datetime import datetime
import feedparser
import httpx
import json
import pathlib
import re
import os
import requests

root = pathlib.Path(__file__).parent.resolve()
client = GraphqlClient(endpoint="https://api.github.com/graphql")

TOKEN = os.environ.get("GITHUB_TOKEN", "")

def replace_chunk(content, marker, chunk, inline=False):
    r = re.compile(
        r"<!\-\- {} starts \-\->.*<!\-\- {} ends \-\->".format(marker, marker),
        re.DOTALL,
    )
    if not inline:
        chunk = "\n{}\n".format(chunk)
    chunk = "<!-- {} starts -->{}<!-- {} ends -->".format(marker, chunk, marker)
    return r.sub(chunk, content)

def make_release_query(after_cursor=None):
    return """
query {
  viewer {
    repositories(first: 100, privacy: PUBLIC, after:AFTER) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        name
        description
        url
        releases(last:1) {
          totalCount
          nodes {
            name
            publishedAt
            url
          }
        }
      }
    }
  }
}
""".replace(
        "AFTER", '"{}"'.format(after_cursor) if after_cursor else "null"
    )

def make_update_query(amount=5):
    return """
{
  viewer {
    name
    repositories(first: FIRST, orderBy: {field: UPDATED_AT, direction: DESC}) {
      nodes {
        owner {
          login
        }
        name,
        updatedAt,
        isPrivate
      }
    }
  }
}
""".replace(
        "FIRST", '{}'.format(amount)
    )

def fetch_updates(oauth_token):
    data = client.execute(
        query=make_update_query(20),
        headers={"Authorization": "Bearer {}".format(oauth_token)},
    )
    print("updates:")
    print(json.dumps(data, indent=4))
    print()
    updates = []
    for u in data["data"]["viewer"]["repositories"]["nodes"]:
        if(len(updates) == 5):
            break
        if(u['name'] != "JaxkDev" and u['owner']['login'] == "JaxkDev" and not u['isPrivate']):
            updates.append(u)
    return updates

def fetch_releases(oauth_token):
    repos = []
    releases = []
    repo_names = set()
    has_next_page = True
    after_cursor = None

    while has_next_page:
        data = client.execute(
            query=make_release_query(after_cursor),
            headers={"Authorization": "Bearer {}".format(oauth_token)},
        )
        print("releases:")
        print(json.dumps(data, indent=4))
        print()
        for repo in data["data"]["viewer"]["repositories"]["nodes"]:
            if repo["releases"]["totalCount"] and repo["name"] not in repo_names:
                repos.append(repo)
                repo_names.add(repo["name"])
                releases.append(
                    {
                        "repo": repo["name"],
                        "repo_url": repo["url"],
                        "description": repo["description"],
                        "release": repo["releases"]["nodes"][0]["name"]
                        .replace(repo["name"], "")
                        .strip(),
                        "published_at": repo["releases"]["nodes"][0]["publishedAt"],
                        "published_day": repo["releases"]["nodes"][0][
                            "publishedAt"
                        ].split("T")[0],
                        "url": repo["releases"]["nodes"][0]["url"],
                    }
                )
        has_next_page = data["data"]["viewer"]["repositories"]["pageInfo"][
            "hasNextPage"
        ]
        after_cursor = data["data"]["viewer"]["repositories"]["pageInfo"]["endCursor"]
    return releases

def get_tils():
    til_readme = "https://raw.githubusercontent.com/0xRinx/TIL/master/README.md"
    r = requests.get(til_readme)
    page = requests.get(til_readme)
    all_text = page.text
    search_re = re.findall( r'(\*+).(\[.*?\])(\(.*?\)).?-(.+)', all_text, re.M|re.I)
    dt_til = sorted(search_re, key=lambda search_re: search_re[3], reverse=True)[:3]

    print('~' * 50)
    print('dt_til upto 3', dt_til)
    print('~' * 50)

    til_md = ""

    for i in dt_til:
        til_md += "\n" + i[0] + ' ' + i[1] + i[2]        

    print('~' * 50)
    print('til_md upto 3', til_md)
    print('~' * 50)

    return til_md

def fetch_blog_entries():
    entries = feedparser.parse("https://0xrinx.is-cool.dev/rss.xml")["entries"]
    return [
        {
            "title": entry["title"],
            "url": entry["link"].split("#")[0],
            "published": entry["published"].split("T")[0],
        }
        for entry in entries
    ]

if __name__ == "__main__":
    readme = root / "README.md"
    project_releases = root / "releases.md"
    
    releases = fetch_releases(TOKEN)
    releases.sort(key=lambda r: r["published_at"], reverse=True)
    md = "\n".join(
        [
            "* [{repo} {release}]({url}) - {published_day}".format(**release)
            for release in releases[:6]
        ]
    )
    readme_contents = readme.open().read()
    rewritten = replace_chunk(readme_contents, "recent_releases", md)

    # Write out full project-releases.md file
    project_releases_md = "\n".join(
        [
            (
                "* **[{repo}]({repo_url})**: [{release}]({url}) - {published_day}\n"
                "<br>{description}"
            ).format(**release)
            for release in releases
        ]
    )
    project_releases_content = project_releases.open().read()
    project_releases_content = replace_chunk(
        project_releases_content, "recent_releases", project_releases_md
    )
    project_releases_content = replace_chunk(
        project_releases_content, "release_count", str(len(releases)), inline=True
    )
    project_releases.open("w").write(project_releases_content)

    updates = fetch_updates(TOKEN)
    updates_md = "\n".join(
        [
            "* [{title}]({url}) - {created_at}".format(
                title=update["name"],
                url="https://github.com/0xRinx/"+update["name"],
                created_at=update["updatedAt"],
            )
            for update in updates
        ]
    )
    rewritten = replace_chunk(rewritten, "recent_updates", updates_md)

    dateTimeObj = datetime.now()
    timestamp = dateTimeObj.strftime("%d-%b-%Y (%H:%M:%S)")
    rewritten = replace_chunk(rewritten, "updated_at", "Last updated at `"+timestamp+" UTC+00`")

    entries = fetch_blog_entries()[:3]
    entries_md = "<br>".join(
        ["• [{title}]({url})".format(**entry) for entry in entries]
    )
    rewritten = replace_chunk(rewritten, "blog", entries_md)

    til_readme_contents = get_tils()
    rewritten = replace_chunk(rewritten, "tilentries", til_readme_contents)

    readme.open("w").write(rewritten)
