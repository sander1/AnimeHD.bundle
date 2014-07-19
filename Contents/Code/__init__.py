PREFIX = "/video/animehd"
NAME = "AnimeHD"
ART = "art-default.jpg"
ICON = "icon-default.png"
START_MENU = [["Ongoing anime", "ongoing"], ["All anime", "all"]]
MP4UPLOAD = [
	Regex('\'file\': \'(http\://.*?\.mp4)\''),
	Regex('\'image\': \'(http\://.*?\.jpg)\'')
]
ARKVID = [
	Regex('src="(http:\/\/.*?)"'), 
	Regex('poster="(http:\/\/.*?)"')
]

class Anime:

	BASE_URL = 'http://www.masterani.me/api/anime'

	def getAnime(self, query = ""):
		try :
			return XML.ObjectFromURL(self.BASE_URL + query)
		except Exception:
			return None

class Video:

	def __init__(self, url):
		self.url = url

	def scrape(self, html, regex):
		found = regex.search(html)
		if found:
			return found.group(1)
		return None

	def get(self, host):
		try:
			src = HTTP.Request(self.url).content
		except Exception:
			Log.Error("[AnimeHD][HTTP] - Could not crawl website") 
			return None
		if src and host:
			if host == "MP4Upload":
				vid = self.scrape(src, MP4UPLOAD[0])
				img = self.scrape(src, MP4UPLOAD[1])
			elif host == "Arkvid":
				vid = self.scrape(src, ARKVID[0])
				img = self.scrape(src, ARKVID[1])

			if vid and img: 
				return [vid, img]
		return None

def Start():
	ObjectContainer.art = R(ART)
	HTTP.CacheTime = 10800

@handler(PREFIX, NAME, thumb=ICON)
def MainMenu():
	oc = ObjectContainer()
	for menu in START_MENU:
		oc.add(DirectoryObject(key = Callback(AnimeList, category = menu[1]), title = menu[0]))
	oc.add(InputDirectoryObject(key = Callback(SearchAnimeList), title = "Search AnimeHD", prompt = "Search for anime?"))
	return oc

def CreateAnimeList(animes, title = "All anime"):
	oc = ObjectContainer(title1 = title)
	for anime in animes.findall('anime'):
		name = anime.find('name').text
		anime_id = anime.find('id').text
		cover = anime.find('cover').text
		oc.add(DirectoryObject(
			key = Callback(EpisodeList, anime = anime_id, cover = cover, name = name),
			title = name,
			summary = "www.masterani.me",
			thumb = Resource.ContentsOfURLWithFallback(url = cover, fallback='icon-cover.png')
		)
	)
	return oc

@route(PREFIX + "/anime")
def AnimeList(category = None):
	if category == None:
		Log.Info("No category has been set.")
	elif category == "all":
		animes = Anime().getAnime()
		if animes:
			return CreateAnimeList(animes)
		else:
			Log.Error("Failed loading anime.")
	elif category == "ongoing":
		animes = Anime().getAnime("/ongoing")
		if animes:
			return CreateAnimeList(animes, "Ongoing anime")
		else:
			Log.Error("Failed loading anime.")

@route(PREFIX + "/anime/search")
def SearchAnimeList(query):
	if query:
		animes = Anime().getAnime("/search/" + query)
		if animes:
			return CreateAnimeList(animes, "Search results: " + query)
		else:
			return ObjectContainer(header="Error", message="Nothing found! Try something less specific or request anime at www.masterani.me") 
	else:
		Log.Error("[AnimeHD] - Must set search query.")

@route(PREFIX + "/episodes")
def EpisodeList(anime , cover, name):
	episodes = Anime().getAnime("/" + anime)
	if episodes:
		oc = ObjectContainer(title1 = name + " - Episodes")
		for episode in episodes.findall('episode'):
			episode_id = episode.find('id').text
			oc.add(DirectoryObject(
				key = Callback(WatchEpisode, anime = anime, episode = episode_id, title = name + " - ep. " + episode_id),
				title = episode_id,
				thumb = Resource.ContentsOfURLWithFallback(url = cover, fallback='icon-cover.png')
			)
		)
		return oc
	else:
		Log.Error("Failed loading episodes for " + name)

@route(PREFIX + "/watch/mirror")
def CreateVideo(url, thumb, anime, episode, resolution, host, include_container=False):
	video_object = VideoClipObject(
		key = Callback(CreateVideo, url=url, thumb=thumb, anime=anime, episode=episode, resolution=resolution, host=host, include_container=True),
		rating_key = url,
		title = host + " - " + resolution + "p",
		thumb = Resource.ContentsOfURLWithFallback(url=thumb, fallback='icon-cover.png'),
		items = [
			MediaObject(
				parts = [PartObject(key=url)],
				optimized_for_streaming = True,
				container = Container.MP4,
				audio_channels = 2,
				audio_codec = AudioCodec.AAC,
				video_resolution = resolution
				)
			]
		)
	if include_container:
		return ObjectContainer(objects=[video_object])
	else:
		return video_object

@route(PREFIX + "/episode")
def WatchEpisode(anime, episode, title):
	mirrors = Anime().getAnime("/" + anime + "/" + episode)
	if mirrors:
		oc = ObjectContainer(title1 = title)
		for mirror in mirrors.findall('mirror'):
			host = mirror.find('host').text
			video = Video(mirror.find('url').text)	
			url = video.get(host)
			quality = mirror.find('quality').text
			if url:
				Log.Info("[AnimeHD][Success] - Loading: " + host + " - res.: " + quality)
				oc.add(CreateVideo(url[0], url[1], anime, episode, quality, host))
			else:
				Log.Error("[AnimeHD][Failed] - Couldn't load video: " + host + ":" + quality)	
	else:
		Log.Error("Failed loading video(s) for " + name + " ep. " + episode)
	return oc