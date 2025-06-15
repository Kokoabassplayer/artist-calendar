# originate by https://python.plainenglish.io/scrape-everythings-from-instagram-using-python-39b5a8baf2e5
# modified by Nuttapong Buttprom (https://kokoabassplayer.github.io/)
# อย่าลืม pip3 install instaloader
# อย่าลืม pip install tqdm

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
        """
        Initializes the scraper class.

        Args:
            loader (instaloader.Instaloader, optional): Pre-authenticated Instaloader instance.
        """
        self.L = loader if loader else instaloader.Instaloader()

    def download_users_profile_picture(self, username):
        """Downloads only the profile picture of the user."""
        self.L.download_profile(username, profile_pic_only=True)

    def download_users_posts_with_periods(self, username, since, until):
        """Downloads posts within a specified date range."""
        posts = instaloader.Profile.from_username(self.L.context, username).get_posts()
        SINCE = datetime.strptime(since, "%Y-%m-%d")
        UNTIL = datetime.strptime(until, "%Y-%m-%d")

        for post in takewhile(lambda p: p.date > SINCE, dropwhile(lambda p: p.date > UNTIL, posts)):
            self.L.download_post(post, username)

    def download_hashtag_posts(self, hashtag):
        """Downloads posts under a specific hashtag."""
        for post in instaloader.Hashtag.from_name(self.L.context, hashtag).get_posts():
            self.L.download_post(post, target="#" + hashtag)

    def get_users_followers(self, username):
        """Gets and saves the followers of the specified user."""
        self.L.login(input("Input your username: "), input("Input your password: "))
        profile = instaloader.Profile.from_username(self.L.context, username)
        with open("follower_names.txt", "a+") as file:
            for followee in profile.get_followers():
                username = followee.username
                file.write(username + "\n")
                print(username)

    def get_users_followings(self, username):
        """Gets and saves the followings of the specified user."""
        self.L.login(input("Input your username: "), input("Input your password: "))
        profile = instaloader.Profile.from_username(self.L.context, username)
        with open("following_names.txt", "a+") as file:
            for followee in profile.get_followees():
                username = followee.username
                file.write(username + "\n")
                print(username)

    def get_post_comments(self, username):
        """Fetches comments from all posts of the specified user."""
        posts = instaloader.Profile.from_username(self.L.context, username).get_posts()
        for post in posts:
            for comment in post.get_comments():
                print(f"comment.id  : {comment.id}")
                print(f"comment.owner.username  : {comment.owner.username}")
                print(f"comment.text  : {comment.text}")
                print(f"comment.created_at_utc  : {comment.created_at_utc}")
                print("************************************************")

    def get_post_info_csv(self, username, since, until, output_folder=None):
        """
        Fetches Instagram post information for a user and writes it to a CSV file.

        Args:
            username (str): Instagram username.
            since (str): Start date in 'YYYY-MM-DD' format.
            until (str): End date in 'YYYY-MM-DD' format.
            output_folder (str, optional): Directory to save the output CSV. Defaults to the current directory.
        """
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
            for _ in takewhile(lambda p: p.date > SINCE, dropwhile(lambda p: p.date > UNTIL, profile.get_posts()))
        )

        with open(output_file, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "Type", "ID", "Profile", "Caption", "Date", "Location", "URL", "TypeName",
                    "MediaCount", "Likes", "Comments", "Video Views", "Is Video", "Engagement Rate",
                    "Hashtags", "Mentions", "Tagged Users", "Followers", "Following", "Image URL"
                ]
            )

            total_followers = profile.followers
            total_following = profile.followees

            for post in tqdm(
                takewhile(lambda p: p.date > SINCE, dropwhile(lambda p: p.date > UNTIL, posts)),
                total=total_posts_in_range,
                desc="Processing posts",
            ):
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
                location = post.location.name if post.location else ""
                tagged_users = " ".join([user.username if hasattr(user, "username") else user for user in post.tagged_users])

                writer.writerow(
                    [
                        "post", post.mediaid, profile.username, caption, post.date, location, post_url, post.typename,
                        post.mediacount, likes, comments, video_views, is_video, engagement_rate, hashtags, mentions,
                        tagged_users, total_followers, total_following, image_url
                    ]
                )
                # Introduce a random delay between requests to avoid hitting rate limits
                time.sleep(random.uniform(1, 3))

        print(f"Data for {username} from {since} to {until} has been successfully written to {output_file}.")

"""
if __name__=="__main__":
    cls = GetInstagramProfile()
    #cls.download_users_profile_picture("best_gadgets_2030")
    #cls.download_users_posts_with_periods(username="kokoabassplayer_rubikk", since="2023-07-01", until="2023-08-01")
    #cls.download_hashtag_posts("ondemandacademy")
    #cls.get_users_followers("best_gadgets_2030")
    #cls.get_users_followings("best_gadgets_2030")
    #cls.get_post_comments("laydline")

    ### วิธีใช้: เปลี่ยน username และ ระยะเวลาที่ด้านล่าง → กดปุ่มรันที่มุมขวาบน → ไฟล์จะถูกวางลงที่โฟลเดอร์เดียวกับที่ไฟล์ของโค๊ดนี้อยู่
    #cls.get_post_info_csv(username="retrospect_official", since="2024-11-01", until="2024-12-01")

    ### แบบกำหนด folder ของ output
    cls.get_post_info_csv(
        username="retrospect_official",
        since="2024-11-01",
        until="2024-12-01",
        output_folder="/Users/kokoabassplayer/Desktop/python/ArtistCalendar/CSV/raw",
    )
"""
