import json
import os
import requests
from exceptions import ResponseException
from clientSecrets import spotiyID, Spotifytoken
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import youtube_dl


class PlayList:
    def _init_(self):
        self.userID = spotiyID
        self.token = Spotifytoken
        self.youtube_client = self.GetYoutubeClient()
        self.allSongsInfo = {}

    # log into Youtube
    def GetYoutubeClient(self):
        # Log Into Youtube, Copied from Youtube Data API
        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "client_secret.json"

        # Get credentials and create an API client
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes
        )
        credentials = flow.run_console()

        # from the Youtube DATA API
        youtube_client = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials
        )
        return youtube_client

    # get my liked videos from Youtube
    def GetLikedVideos(self):
        request = self.youtube_client.videos().list(
            part="snippet,contentDetails,statistics", myRating="like"
        )
        response = request.execute()

        # collect videos and data from them
        for item in response["items"]:
            video_title = item["snippet"]["title"]
            youtubeUrl = "https://www.youtube.com/watch?v={}".format(item["id"])

            # collect song name using youtube_dl
            video = youtube_dl.YoutubeDL({}).extract_info(youtubeUrl, download=False)
            songName = video["track"]
            artist = video["artist"]

            self.allSongsInfo[video_title] = {
                "youtubeUrl": youtubeUrl,
                "songName": songName,
                "artist": artist,
                # add the uri
                "spotifyUri": self.GetSpotifyURI(songName, artist),
            }

    # create a new playlist
    def CreatePlaylist(self):
        request = json.dumps(
            {
                "name": "Liked Youtube Videos",
                "description": "All my liked Youtube videos",
                "public": "True",
            }
        )
        EndPoint = "https://api.spotify.com/v1/users/{user_id}/playlists".format()
        response = requests.post(
            EndPoint,
            data=request,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer{}".format(self.Spotifytoken),
            },
        )
        response_json = response.json()
        return response_json["id"]  # returns playlist id

    # search for the song
    def GetSpotifyURI(self, songName, artist):
        EndPoint = "https://api.spotify.com/v1/search".format(songName, artist)
        response = requests.post(
            EndPoint,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer{}".format(Spotifytoken),
            },
        )
        response_json = response.json()
        songs = response_json["tracks"]["items"]
        uri = songs[0]["uri"]
        return uri

    # add song into the spotify playlist we created
    def AddSong(self):
        # populate song dictionary
        self.GetLikedVideos()
        # collect all uris
        uris = []
        for song, info in self.allSongsInfo.items():
            uris.append(info["spotifyUri"])
        # create a new playlist
        playlistID = self.CreatePlaylist()
        # add songs into new playlist
        requestData = json.dumps(uris)
        EndPoint = "https://api.spotify.com/v1/tracks/{id}".format(playlistID)

        response = requests.post(
            EndPoint,
            data=requestData,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer{}".format(Spotifytoken),
            },
        )
        if response.status_code != 200:
            raise ResponseException(response.status_code)

        response_json = response_json()
        return response_json