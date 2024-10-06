import os
import time
import json
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth
from tqdm import tqdm

# Load environment variables from .env file
load_dotenv()

# URL of the custom node list
url = "https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/custom-node-list.json"

def get_stars(github_url):
    # Extract owner and repo from the GitHub URL
    parts = github_url.split('/')
    owner, repo = parts[-2], parts[-1].replace('.git', '')
    
    # GitHub API endpoint
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    
    # Get GitHub token from environment variable
    github_token = os.getenv('GITHUB_TOKEN')
    
    try:
        if github_token:
            response = requests.get(api_url, auth=HTTPBasicAuth(github_token, 'x-oauth-basic'))
        else:
            response = requests.get(api_url)
        response.raise_for_status()
        repo_data = response.json()
        return repo_data['stargazers_count']
    except requests.RequestException:
        return "N/A"

def fetch_node_list():
    response = requests.get(url)
    response.raise_for_status()  # Check if the request was successful
    return response.json()

def filter_git_clone_nodes(data):
    # url must starts with https://github.com
    return [node for node in data["custom_nodes"] if node.get("install_type") == "git-clone" and node.get('files')[0].startswith("https://github.com")]

def generate_readme(filtered_nodes):
    old_url_stars = [] # url star data stores sliding window of 7 days
    if os.path.exists('./data/url_stars.json'):
        with open('./data/url_stars.json', 'r') as f:
            old_url_stars = json.load(f)

    with open("README.md", "w") as readme:
        readme.write("# Awesome ComfyUI Custom Nodes\n\n")
        readme.write("Welcome to the Awesome ComfyUI Custom Nodes list! The information in this list is fetched from ComfyUI Manager, ensuring you get the most up-to-date and relevant nodes. This is a curated collection of custom nodes for ComfyUI, designed to extend its capabilities, simplify workflows, and inspire creativity.\n\n")
        readme.write("Whether you're an AI researcher, hobbyist, or someone pushing the boundaries of generative models, these nodes can streamline your work. Data updated daily.\n\n")
        # Add Table of Contents
        readme.write("## Table of Contents\n\n")
        readme.write("- [New Workflows](#new-workflows)\n")
        readme.write("- [Trending Workflows](#trending-workflows)\n")
        readme.write("- [All Workflows Sorted by GitHub Stars](#all-workflows-sorted-by-github-stars)\n")
        readme.write("- [License](#license)\n\n")
        url_stars = {}
        for index, node in enumerate(tqdm(filtered_nodes)):
            github_url = node.get('files')[0]
            stars = get_stars(github_url)
            url_stars[github_url] = stars
            # sleep for 30 seconds every 200 nodes
            if index != 0 and index % 200 == 0:
                time.sleep(30)

        # # save it to ./data/tmp.json
        with open('./data/tmp.json', 'w') as f:
            json.dump(url_stars, f)
    
        # load it from ./data/tmp.json
        # with open('./data/tmp.json', 'r') as f:
        #     url_stars = json.load(f)
        
        # compare with old_url_stars and filter out new nodes
        new_node_urls = []
        for url, stars in url_stars.items():
            if url not in old_url_stars[0]:
                new_node_urls.append(url)
        # sort new nodes by stars, take top 10
        new_node_urls = sorted(new_node_urls, key=lambda x: url_stars[x], reverse=True)[:10]
        readme.write("## New Workflows\n\n")
        # write new_nodes to README.md
        if len(new_node_urls) > 0:
            for url in new_node_urls:
                node = next((node for node in filtered_nodes if node.get('files')[0] == url), None)
                if node:
                    description = node.get('description').split('\n')[0]
                    readme.write(f"- [**{node.get('title')}**]({node.get('files')[0]}): {description}\n")
        else:
            readme.write("No new workflows this week.\n")

        # calculate star increase
        star_increase = {}
        for url, stars in url_stars.items():
            if url in old_url_stars[0]:
                star_increase[url] = stars - old_url_stars[0][url]
        # sort star_increase by stars, take top 10
        star_increase = sorted(star_increase.items(), key=lambda x: x[1], reverse=True)[:10]
        readme.write("## Trending Workflows\n\n")
        # write star_increase to README.md
        if len(star_increase) > 0:    
            for url, stars in star_increase:
                node = next((node for node in filtered_nodes if node.get('files')[0] == url), None)
                if node:
                    description = node.get('description').split('\n')[0]
                    star_increase_text = f" (⭐+{stars})" if stars > 0 else ""
                    readme.write(f"- [**{node.get('title')}**]({node.get('files')[0]}){star_increase_text}: {description}\n")
        else:
            readme.write("No trending workflows this week.\n")

        # All Workflows Sorted by GitHub Stars
        readme.write("## All Workflows Sorted by GitHub Stars\n\n")
        for url, stars in sorted(url_stars.items(), key=lambda x: x[1], reverse=True):
            node = next((node for node in filtered_nodes if node.get('files')[0] == url), None)
            if node:
                description = node.get('description').split('\n')[0]
                readme.write(f"- [**{node.get('title')}**]({node.get('files')[0]}): {description}\n")

        # Write source and license information
        readme.write("\n## Source\n\n")
        readme.write("This list is generated from the data provided by [ComfyUI-Manager](https://github.com/ltdrdata/ComfyUI-Manager).\n\n")
        
        readme.write("## License\n\n")
        readme.write("This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.\n")
        
        # write url_stars ./data/url_stars.json
        with open('./data/url_stars.json', 'w') as f:
            # sliding window of 7 days
            old_url_stars.append(url_stars)
            if len(old_url_stars) > 7:
                old_url_stars.pop(0)
            json.dump(old_url_stars, f)

def main():
    data = fetch_node_list()
    filtered_nodes = filter_git_clone_nodes(data)
    generate_readme(filtered_nodes)
    print(f"Processed {len(filtered_nodes)} git-clone nodes.")

if __name__ == "__main__":
    main()
