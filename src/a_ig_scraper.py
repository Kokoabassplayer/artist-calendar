import instaloader
from datetime import datetime
from itertools import dropwhile, takewhile
import csv
import time
from tqdm import tqdm
import re
import os
import random

class GetInstagramProfile:
    def __init__(self, loader=None) -> None:
        self.L = loader if loader else instaloader.Instaloader()

    def get_post_info_csv(self, username, since, until, output_folder=None):
        SINCE = datetime.strptime(since, "%Y-%m-%d")
        UNTIL = datetime.strptime(until, "%Y-%m-%d")
        if output_folder:
            os.makedirs(output_folder, exist_ok=True)
        else:
            output_folder = os.getcwd()
        output_file = os.path.join(output_folder, f"{username}_{since}_to_{until}.csv")
        profile = instaloader.Profile.from_username(self.L.context, username)
        posts = profile.get_posts()
        total_posts_in_range = sum(
            1
            for _ in takewhile(lambda p: SINCE <= p.date <= UNTIL, profile.get_posts())
        )
        with open(output_file, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "Type", "ID", "Profile", "Caption", "Date", "Location",
                    "URL", "TypeName", "MediaCount", "Likes", "Comments",
                    "Video Views", "Is Video", "Engagement Rate", "Hashtags",
                    "Mentions", "Tagged Users", "Followers", "Following", "Image URL"
                ]
            )
            total_followers = profile.followers
            total_following = profile.followees
            for post in tqdm(
                takewhile(lambda p: SINCE <= p.date <= UNTIL, posts),
                total=total_posts_in_range,
                desc="Processing posts",
            ):
                retries = 3  # Set the number of retries for a post
                while retries > 0:
                    try:
                        image_url = post.url
                        caption = post.caption or ""
                        hashtags = " ".join(re.findall(r"#[^\s]+", caption))
                        post_url = "https://www.instagram.com/p/" + post.shortcode
                        likes = post.likes
                        comments = post.comments
                        video_views = post.video_view_count if post.is_video else ""
                        is_video = post.is_video
                        engagement_rate = (likes + comments) / total_followers * 100
                        mentions = " ".join(post.caption_mentions)
                        location = post.location.name if post.location else "Unknown"
                        tagged_users = " ".join(
                            [user.username if hasattr(user, "username") else user for user in post.tagged_users]
                        )
                        writer.writerow(
                            [
                                "post", post.mediaid, profile.username, caption, post.date, location,
                                post_url, post.typename, post.mediacount, likes, comments,
                                video_views, is_video, engagement_rate, hashtags, mentions,
                                tagged_users, total_followers, total_following, image_url
                            ]
                        )
                        break  # Break the retry loop on success
                    except Exception as e:
                        retries -= 1
                        print(f"Error processing post {post.mediaid}: {e}. Retries left: {retries}")
                        time.sleep(random.uniform(1, 3))  # Random delay before retrying
                else:
                    print(f"Skipping post {post.mediaid} after multiple failed attempts.")
                time.sleep(random.uniform(1, 3))
        print(f"Data for {username} from {since} to {until} has been successfully written to {output_file}.")

if __name__ == "__main__":
    cls = GetInstagramProfile()
    cls.get_post_info_csv(
        username="retrospect_official",
        since="2024-11-01",
        until="2024-12-01",
        output_folder="/Users/kokoabassplayer/Desktop/python/ArtistCalendar/CSV/raw"
    )