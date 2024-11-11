import time
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from tqdm import tqdm

# Prompt the user for the Slack token
slack_token = input("Enter your Slack Bot Token: ")

# Initialize the Slack client with the token provided by the user
client = WebClient(token=slack_token)

def get_user_id_by_email(email):
    """
    Function to get the user ID from an email address.
    :param email: Email address of the user
    :return: Slack user ID, Slack username
    """
    print(f"Looking up user ID for email: {email}")
    try:
        response = client.users_lookupByEmail(email=email)
        user_id = response["user"]["id"]
        user_name = response["user"]["real_name"]
        print(f"User ID for {email}: {user_id}")
        return user_id, user_name
    except SlackApiError as e:
        print(f"Error fetching user ID for email {email}: {e.response['error']}")
        return None, None

def get_channel_ids():
    """
    Function to retrieve all non-archived channel IDs (public and private) in the workspace, handling pagination.
    :return: Dictionary of {channel_id: channel_name} for non-archived channels and counts of public and private channels.
    """
    print("Fetching all non-archived channel IDs (including private channels)...")
    all_channels = {}
    public_channel_count = 0
    private_channel_count = 0
    cursor = None

    try:
        while True:
            # Fetch a page of public and private channels, excluding archived ones
            response = client.conversations_list(types="public_channel,private_channel", limit=100, cursor=cursor)
            channels = response["channels"]
            
            # Store non-archived channel ID and name, and count public/private channels
            for channel in channels:
                if not channel["is_archived"]:  # Skip archived channels
                    all_channels[channel["id"]] = channel["name"]
                    if channel["is_private"]:
                        private_channel_count += 1
                    else:
                        public_channel_count += 1

            # Check if there's more data (pagination)
            cursor = response["response_metadata"].get("next_cursor", None)
            if not cursor:
                break
    except SlackApiError as e:
        print(f"Error fetching channels: {e.response['error']}")
    
    # Print the total number of channels found (public and private)
    print(f"Total channels found: {len(all_channels)}")
    print(f"Public channels: {public_channel_count}")
    print(f"Private channels: {private_channel_count}")
    
    return all_channels

def get_users_channel_ids(user_id_1, user_id_2, all_channel_ids):
    """
    Function to get the list of channels both users are members of.
    :param user_id_1: Slack user ID of the first user
    :param user_id_2: Slack user ID of the second user
    :param all_channel_ids: List of all channel IDs to check membership for
    :return: Two dictionaries, one for each user's channel IDs
    """
    print(f"Fetching channel membership for both users...")
    user_1_channels = set()
    user_2_channels = set()

    try:
        # Wrap the loop with tqdm to show the progress bar
        for channel_id in tqdm(all_channel_ids, desc="Checking channel memberships", unit="channel"):
            while True:
                try:
                    members_response = client.conversations_members(channel=channel_id)

                    # Check membership for both users
                    if user_id_1 in members_response["members"]:
                        user_1_channels.add(channel_id)
                    if user_id_2 in members_response["members"]:
                        user_2_channels.add(channel_id)

                    # Add a delay to avoid rate limiting
                    time.sleep(1)  # Adjust this based on your rate limit tolerance
                    break  # Exit the while loop if successful

                except SlackApiError as e:
                    if e.response['error'] == 'ratelimited':
                        # Handle rate-limiting by checking the Retry-After header
                        retry_after = int(e.response.headers.get('Retry-After', 1))
                        print(f"Rate-limited. Retrying after {retry_after} seconds...")
                        time.sleep(retry_after)
                    else:
                        # Handle other API errors
                        print(f"Error fetching channel members for channel {channel_id}: {e.response['error']}")
                        break

    except SlackApiError as e:
        print(f"Error fetching channel memberships: {e.response['error']}")
    
    return user_1_channels, user_2_channels

def compare_user_channels(email_1, email_2):
    """
    Compares the channels of two users identified by their emails and prints the difference.
    :param email_1: Email of the first user
    :param email_2: Email of the second user
    """
    print(f"Comparing channels for {email_1} and {email_2}...\n")

    # Get the user IDs and names by their email addresses
    user_id_1, user_name_1 = get_user_id_by_email(email_1)
    user_id_2, user_name_2 = get_user_id_by_email(email_2)

    # If either user ID is None, exit
    if not user_id_1 or not user_id_2:
        print("Unable to retrieve user IDs for comparison.")
        return

    # Fetch all channel IDs and names in the workspace
    all_channels = get_channel_ids()

    # Get the channels for both users
    channels_user_1, channels_user_2 = get_users_channel_ids(user_id_1, user_id_2, all_channels.keys())

    # Print how many channels each user is a member of
    print(f"{user_name_1} is part of {len(channels_user_1)} channels.")
    print(f"{user_name_2} is part of {len(channels_user_2)} channels.")

    print("\nComparing channel memberships...")

    # Channels only in user 1
    only_in_user_1 = channels_user_1 - channels_user_2
    # Channels only in user 2
    only_in_user_2 = channels_user_2 - channels_user_1

    # Output the results with sorted channel names
    if only_in_user_1:
        print(f"\nChannels only in {user_name_1}:")
        for channel_name in sorted([all_channels[channel_id] for channel_id in only_in_user_1]):
            print(f"- {channel_name}")
    else:
        print(f"\nNo channels are exclusive to {user_name_1}.")

    if only_in_user_2:
        print(f"\nChannels only in {user_name_2}:")
        for channel_name in sorted([all_channels[channel_id] for channel_id in only_in_user_2]):
            print(f"- {channel_name}")
    else:
        print(f"\nNo channels are exclusive to {user_name_2}.")

# Prompt the user for the email addresses
email_1 = input("Enter the first user's email address: ")
email_2 = input("Enter the second user's email address: ")

# Run the comparison
compare_user_channels(email_1, email_2)