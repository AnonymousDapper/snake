""" Spotify / Youtube API """

import aiohttp
import json
import asyncio
import base64
import re
import xxhash

from datetime import datetime
from os.path import isfile

# YoutubeDL - to fully extract info and download url

from youtube_dl import YoutubeDL
from youtube_dl.extractor.youtube import YoutubeIE


def _read_json(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

class YoutubeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, YoutubeVideo):
            return {
                "data": {
                    "id": obj.id,
                    "snippet": {
                        "title": obj.title,
                        "description": obj.description,
                        "channelTitle": obj.uploader,
                        "thumbnails": {
                            "high": {
                                "url": obj.thumbnail_url
                            }
                        }
                    }
                },
                "ytdl_data": {
                    "duration": obj.duration,
                    "ext": obj.extension,
                    "url": obj.download_url
                }
            }

        return json.JSONEncoder.default(self, obj)

class SpotifyPlaylist:
    def __init__(self, api, data):
        self.id = data["id"]
        self.name = data["name"]
        self.owner = data["owner"]["id"]
        self.total_tracks = data["tracks"]["total"]

        self.api = api

        self.tracks = []

    async def load_tracks(self):
        self.tracks = await self.api._fetch_playlist_tracks(self.owner, self.id)

    def to_youtube_playlist(self, api):
        return YoutubePlaylist(api, self)

    def __repr__(self):
        return f"<SpotifyPlaylist(id={self.id}, name='{self.name}', owner_id='{self.owner}', total_tracks={self.total_tracks}, hash={hash(self)})>"

    def __hash__(self):
        id_string = ("-".join(track["id"] for track in self.tracks)) if len(self.tracks) > 0 else self.id
        xer = xxhash.xxh64(bytes(id_string, "utf-8"))

        return xer.intdigest()

class SpotifyAPI:
    def __init__(self):
        credentials = _read_json("credentials.json")

        self.client_id = credentials["spotify_id"]
        self.client_secret = credentials["spotify_key"]
        self.access_token = {
            "token": None,
            "expires_at": datetime.now().timestamp()
        }

        self.http_session = aiohttp.ClientSession()

    def _clean_album_structure(self, obj):
        track_list = []
        for info in obj["items"]:
            track = info["track"]
            track_list.append({
                "title": track["name"],
                "album": track["album"]["name"],
                "artists": [artist["name"] for artist in track["artists"]],
                "id": track["id"]
            })

        return track_list

    def _get_playlist_details(self, url):
        url_parts = url.strip("/").split("/")
        return url_parts[-3], url_parts[-1]

    async def _get_access_token(self):
        basic_token = "Basic " + base64.b64encode(bytes(self.client_id + ":" + self.client_secret, encoding="utf-8")).decode("utf-8")

        async with self.http_session.post("https://accounts.spotify.com/api/token", data=dict(grant_type="client_credentials"), headers=dict(Authorization=basic_token)) as token_response:
            response_data = await token_response.json()

            if response_data.get("access_token") and response_data.get("expires_in"):
                self.access_token["token"] = "Bearer " + response_data["access_token"]
                self.access_token["expires_at"] = datetime.now().timestamp() + response_data["expires_in"]

            elif response_data.get("error"):
                raise RuntimeError(response_data["error_description"])

    async def _fetch_playlist_tracks(self, user_id, playlist_id, offset=0):
        tracks = None

        await self.refresh_token()
        async with self.http_session.get(f"https://api.spotify.com/v1/users/{user_id}/playlists/{playlist_id}/tracks", params={"offset":offset, "fields":"items(track(name,id,artists(name),album(name))),total,limit"}, headers=dict(Authorization=self.access_token["token"])) as playlist_info:
            list_data = await playlist_info.json()


            if list_data.get("error") is None:
                tracks = self._clean_album_structure(list_data)

                if list_data["total"] > (offset + 100):
                    future_tracks = await self._fetch_playlist_tracks(user_id, playlist_id, offset=offset + 100)
                    tracks += future_tracks

            elif list_data.get("error"):
                raise RuntimeError(f"{playlist_data['error']['status']} - {playlist_data['error']['message']}")

        return tracks

    async def refresh_token(self):
        if self.access_token["expires_at"] < datetime.now().timestamp():
            print("refreshing token")
            await self._get_access_token()

        else:
            print(f"Access token expires at {datetime.fromtimestamp(self.access_token['expires_at']):%a %B %d, %Y, %H:%M:%S}")

    async def get_playlist(self, url):
        await self.refresh_token()

        user_id, playlist_id = self._get_playlist_details(url)

        async with self.http_session.get(f"https://api.spotify.com/v1/users/{user_id}/playlists/{playlist_id}", params={"fields": "name,id,owner(id),tracks(total)"}, headers=dict(Authorization=self.access_token["token"])) as playlist_response:
            playlist_data = await playlist_response.json()

            if playlist_data.get("error") is None:
                return SpotifyPlaylist(self, playlist_data)

            else:
                raise RuntimeError(f"{playlist_data['error']['status']} - {playlist_data['error']['message']}")

class YoutubeVideo:
    def __init__(self, data, ytdl_data):
        self.id = data["id"]
        self.title = data["snippet"]["title"]
        self.description = data["snippet"]["description"]
        self.thumbnail_url = data["snippet"]["thumbnails"]["high"]["url"]
        self.uploader = data["snippet"]["channelTitle"]

        self.duration = ytdl_data.get("duration")
        self.extension = ytdl_data.get("ext")
        self.download_url = ytdl_data.get("url")

    def get_duration(self):
        days, hours, minutes, seconds = 0, 0, 0, 0
        minutes, seconds = divmod(self.duration, 60)

        if minutes > 60:
            hours, minutes = divmod(minutes, 60)

            if hours > 24:
                days, hours = divmod(hours, 24)

        return f"{str(days) + 'd' if days else ''}{str(hours) + 'h' if hours else ''}{str(minutes) + 'm' if minutes else ''}{str(seconds) + 's' if seconds else ''}"

    def get_url(self):
        return f"https://youtu.be/{self.id}"

    def __repr__(self):
        return f"<YoutubeVideo(id={self.id}, title='{self.title}', uploader='{self.uploader}', url='<{self.get_url()}>', duration='{self.get_duration()}')>"


class YoutubePlaylist:
    def __init__(self, api, source_playlist:SpotifyPlaylist):
        self.api = api
        self.tracks = []
        self.playlist_id = source_playlist.id

        if len(source_playlist.tracks) > source_playlist.total_tracks:
            asyncio.run_coroutine_threadsafe(source_playlist.load_tracks())

        self.spotify_tracks = source_playlist.tracks
        self.playlist_hash = hash(source_playlist)

    def _write_cache(self):
        if len(self.tracks) > 0:
            with open(f"./playlist_cache/{self.playlist_id}.json", "w", encoding="utf-8") as f:
                json.dump({"hash": self.playlist_hash, "tracks": self.tracks}, f, cls=YoutubeEncoder)

    def _load_cache(self):
        if isfile(f"./playlist_cache/{self.playlist_id}.json"):
            with open(f"./playlist_cache/{self.playlist_id}.json", "r", encoding="utf-8") as f:
                try:
                    track_data = json.load(f)

                except:
                    return False, None

                print(f"loaded cache {track_data['hash']}")

                if track_data["hash"] == self.playlist_hash:
                    return True, [YoutubeVideo(track["data"], track["ytdl_data"]) for track in track_data["tracks"]]

                else:
                    return False, None

        else:
            return False, None

    async def load_tracks(self):
        success, data = self._load_cache()

        if success:
            self.tracks = data
            return []

        else:
            failed_tracks = []

            for track in self.spotify_tracks:
                track_info = await self.api.search_videos(f"{track['artists'][0]} {track['title']}")

                print(track_info)

                if len(track_info) == 0:
                    failed_tracks.append(track)

                else:
                    track_id = track_info[0]['id']
                    video_result = await self.api.get_video_from_id(track_id)
                    self.tracks.append(video_result)

            self._write_cache()
            return failed_tracks

    def __repr__(self):
        return f"<YoutubePlaylist(id={self.playlist_id}, hash={self.playlist_hash}, total_tracks={len(self.tracks)})>"

class YoutubeAPI:
    def __init__(self):
        credentials = _read_json("credentials.json")

        self.api_key = credentials["google_key"]

        self.http_session = aiohttp.ClientSession()

        self.ytdl = YoutubeDL({
            "format": "webm[abr>0]/bestaudio/best",
            "restrictfilenames": True,
            "noplaylist": True,
            "nocheckcertificate": True,
            "ignoreerrors": False,
            "logtostderr": False,
            "quiet": True,
            "no_warnings": True,
            "default_search": "error",
            "source_address": "0.0.0.0",
            "prefer_ffmpeg": True
        })

        self.extractor = YoutubeIE()
        self.extractor._downloader = self.ytdl

        self.raw_video_id_regex = re.compile(r"^([\w-]+)$")
        self.video_id_regex = re.compile(r"watch/?\?v=([\w-]+)")
        self.playlist_id_regex = re.compile(r"playlist/?\?list=([\w-]+)")

    def determine_query_type(self, query):
        raw_video_match = self.raw_video_id_regex.search(query)
        video_match = self.video_id_regex.search(query)
        playlist_match = self.playlist_id_regex.search(query)

        print(raw_video_match, video_match, playlist_match, query)

        if raw_video_match is not None:
            return "video", raw_video_match.group(1)

        elif video_match is not None:
            return "video", video_match.group(1)

        elif playlist_match is not None:
            return "playlist", playlist_match.group(1)

        else:
            return "search", query

    async def get_video_from_id(self, video_id):
        async with self.http_session.get("https://www.googleapis.com/youtube/v3/videos", params={"part": "snippet", "id": video_id, "fields": "items(id,snippet(channelTitle,description,thumbnails/high/url,title))", "key": self.api_key}) as video_response:

            if video_response.status == 200:
                video_data = await video_response.json()

                ytdl_data = self.ytdl.process_video_result(self.extractor.extract(f"https://youtube.com/watch?v={video_id}"), download=False)

                return YoutubeVideo(video_data["items"][0], ytdl_data)

            else:
                print(video_response.status, await video_response.text())

    async def search_videos(self, search_query):
        async with self.http_session.get("https://www.googleapis.com/youtube/v3/search", params={"part": "snippet", "order": "viewCount", "fields": "items(id(playlistId,videoId),snippet(channelTitle,title))", "type": "video", "q": search_query, "maxResults": 5, "key": self.api_key}) as search_response:

            if search_response.status == 200:
                search_data = await search_response.json()

                return [{"id": video["id"]["videoId"], "title": video["snippet"]["title"], "channel": video["snippet"]["channelTitle"]} for video in search_data["items"]]

            else:
                print(search_response.status, await search_response.text())


