# Mavis Trello → Jira Migrator

The `jira.py` script scrapes the Trello board as described in the `.env` file. It was initially written for `Python 3.12.6`.

Because Jira likely doesn't have permission to access the attachments directly on Trello's servers, this script also
downloads the files' contents and saves them in files on the local machine. The `attachment_server.py` script can
then be used to serve these files to Jira, likely via an IP tunnel.

## General functionality

A broad overview of how this script works:
1. Uses Trello's API get a list of every card on the specified board.
2. For every card, extract the relevant details, and append it to in an output array
    1. For each attachment on the board, save it to a unique file name, and add to the output the corresponding
       URL which will serve the local version of the saved attachment (more on this later).
3. Write all this info to a `.csv` file.

Once the script has run:
1. Spin up the local server in `attachment_server.py`. This is where Jira will get the attachment data from.
2. Set up an IP tunnel (or change your router/firewall settings) to allow `localhost:3000` to be exposed to the wider
   internet.
   1. As I didn't have admin access to the router at my workplace, I used an IP tunnel
   2. A lot of IP tunnels (eg `ngrok`, `localtunnel`) have a landing page the first time you visit their URL, which
      makes it unusable for this application because Jira needs to access the data on the first try, without needing
      to click a "bypass" button.
   3. As such, I ended up using [pagekite](https://pagekite.net/), which served these purposes very well.

## Usage instructions

⚠️ There are a couple of TODOs in the Python code, which may need to be actioned if you'd like to use that functionality.
It only caused an issue for 3 (out of 420) of our cards. ⚠️

1. Get a Trello API key, and token.
2. Add your Trello board's data to the `.env` file.
3. Populate the `.json` config files. It's possible to get lists of these things from the
   [Trello API](https://developer.atlassian.com/cloud/trello/rest). E.g. for the `labels`, send a `GET` request to
   `https://api.trello.com/1/boards/[BOARD_ID/lists` with your key and token as headers.
   1. Edit the `columns_mapping.json` to reflect how your Trello columns will map to the Jira columns.
   2. Edit the `jira_labels.json` to include in inclusive list of label values to use in Jira (any Trello labels which
      don't match (case-insensitive) will be discarded).
   3. Populate the `members_mapping.json` file to map your users' Trello IDs to their Jira username (HSCIC shortcode).
4. Set up an IP tunnel, or (if you have access to your router) set up port forwarding and a firewall rule. Save this
   endpoint in the `.env` file as well, e.g. `https://XXXXX.pagekite.me/`.
5. Install Python (this was initially created using `Python 3.12.6`).
6. Install dependencies:
    ```zsh
    pip install -r requirements.txt
    ```
7. Run the script to scrape the information you need from Trello:
    ```zsh
    python jira.py
    ```
8. Spin up the attachments server:
    ```zsh
    python attachments_server.py
    ```
9. Start the Jira import using the `.csv` file generated in Step 7. Note that you must be a Jira site admin
   (not a board admin) in order to access many of the fields (e.g. card creation time, comments, attachments).


# Mavis Trello Card Extractor

The `analyse.py` script extracts cards with specific labels from a Trello board JSON export and saves them to a CSV file.

## Usage

```bash
python analyse.py trello-board.json cards.csv --labels "bug,v1.4.0"
```
