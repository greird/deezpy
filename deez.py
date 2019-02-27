from flask import Flask, redirect, request, session, json, jsonify, render_template
import ConfigParser, requests, re, os, time, sets

config_file = ConfigParser.RawConfigParser()   
config_file.read('config.cfg')

app = Flask(__name__)
CONFIG = {
	'APP_ID': config_file.get('deezer-api', 'APP_ID'),
	'APP_SECRET': config_file.get('deezer-api', 'APP_SECRET'),
	'IP': config_file.get('flask-server', 'IP'),
	'PORT': int(config_file.get('flask-server', 'PORT')),
	'DEBUG': config_file.get('flask-server', 'DEBUG'),
	'CACHE_DURATION': int(config_file.get('cache', 'DURATION'))
}

@app.route("/")
def index():
	"""
		If token exists, display; else redirect to auth
	"""
	if isAuth():
		return render_template('index.html')
	else:
		return redirect("/auth")

@app.route("/logout")
def logout():
	"""
		Logout
	"""
	session.clear()
	return render_template('index.html')

@app.route("/auth")
def auth():
	"""
		Open Deezer auth window if user is not already logged in, ask for permission and redirect to previous url
	"""
	code = request.args.get('code')
	perms = request.args.get('perms') if request.args.get('perms') is not None else "basic_access"

	if code is None:
		redirect_uri = request.base_url
		dzr_auth_url = 'https://connect.deezer.com/oauth/auth.php?app_id=' + CONFIG['APP_ID'] +'&perms=' + perms +'&redirect_uri=' + redirect_uri + '&format=channel'
		
		try:
			return redirect(dzr_auth_url)
		except Exception as e:
			error = request.args.get('error')
			if error is not None:
				return redirect("/?error=" + error)
			else:
				return redirect("/?error=" + e)
	
	else:
		dzr_token_url = ('https://connect.deezer.com/oauth/access_token.php' 
			'?app_id=' + CONFIG['APP_ID'] +
			'&secret=' + CONFIG['APP_SECRET'] + 
			'&code=' + code
			)
		r = requests.get(dzr_token_url) 

		try:
			session['token'] = re.search(r'access_token=([a-zA-Z0-9]+)', r.text).group(1)
			expires = int(re.search(r'expires=([0-9]+)', r.text).group(1))
			
			# Fetch user details
			r_user = dzrGet("/user/me", cache=False)

			session['expire'] = (time.time() + expires) if expires != 0 else 0 # 0 if offline_access requested
			session['id'] = str(r_user['id'])
			session['name'] = r_user['name']
			session['picture'] = r_user['picture_medium']
			
			r_perms = dzrGet("/user/me/permissions", cache=False)
			session['perms'] = []
			for perm in r_perms['permissions']:
				if perm:
					session['perms'].append(perm)

		except Exception as e:
			return redirect("/?error=" + r.text)

		if 'redirect' in session:
			back_url = session['redirect']
			session.pop('redirect', None)
			return redirect(back_url)
		else:
			return redirect("/")

@app.route("/update/<string:playlist_id>", methods=['GET', 'POST']) # TODO: should be /playlist/id/update?tracks=
def update(playlist_id):
	"""
		Update a playlist
	"""
	if isAuth("basic_access", "manage_library"):
		tracks = request.args.get('tracks', '')

		r = requests.post("http://api.deezer.com/2.0/playlist/" + playlist_id + "/tracks", data = {'access_token': session['token'], 'songs': tracks})
		response = r.json()

		try:
			iterator = iter(response)
		except TypeError:
			return redirect("/playlist/" + playlist_id)
		else:
			return redirect("/?error=" + response['error']['message'])
	else:
		return redirect("/auth?perms=basic_access,manage_library")

@app.route("/create", methods=['GET', 'POST'])
@app.route("/create/<playlist_title>", methods=['GET', 'POST'])
def create(playlist_title='New playlist'):
	"""
		Create a playlist and fill it with given tracks
	"""
	if isAuth("basic_access", "manage_library"):
		tracks = request.args.get('tracks', '')

		r = requests.post("http://api.deezer.com/2.0/user/" + session['id'] + "/playlists", data = {'access_token': session['token'], 'title': playlist_title})
		response = r.json()

		try:
			iterator = iter(response)
		except TypeError:
			return redirect("/?error=" + r.text)
		else:
			playlist_id = str(response['id'])
			if len(tracks) == 0:
				playlist_url = 'http://www.deezer.com/playlist/' + playlist_id
				return redirect('/playlist/' + playlist_id)
			else:
				return redirect('/update/' + playlist_id + '?tracks=' + tracks)
	else:
		return redirect("/auth?perms=basic_access,manage_library")

@app.route('/track/<string:track_id>')
def track(track_id):
	"""
		Display a track
	"""
	track_id = track_id.split(',')
	if isAuth():
		items = []
		for id in track_id:
			r = dzrGet("/track/" + id)
			items.append(r)

		if len(items) > 1:
			items = map(standardize, items)
			return render_template('list.html', item=items, title=request.args.get('title', None))
		else:
			return render_template('track.html', track=items[0])
	else:
		return redirect("/auth")

@app.route('/playlist/<string:playlist_id>')
def playlist(playlist_id):
	"""
		Display a playlist, a list of playlist or 2 playlist side by side
	"""
	playlist_id = playlist_id.split(',')
	if isAuth():
		items = []
		for item in playlist_id:
			r = dzrGet("/playlist/" + item)
			items.append(r)

		# Display a list of playlists
		if len(items) > 2:
			items = map(standardize, items)
			return render_template('list.html', item=items, title=request.args.get('title', None))

		# Display 2 playlists side by side
		elif len(items) == 2:
			a_ids = set([i['id'] for i in items[0]['tracks']['data']])
			b_ids = set([i['id'] for i in items[1]['tracks']['data']])
			intersection = list(a_ids.intersection(b_ids))

			return render_template('compare.html', items=(items[0], items[1]), intersection=intersection)

		# Display all the details for 1 playlist
		else:
			return render_template('playlist.html', playlist=items[0])
	else:
		return redirect("/auth")

@app.route('/album/<string:album_id>')
def album(album_id):
	"""
		Display an album
	"""
	album_id = album_id.split(',')
	if isAuth():
		items = []
		for item in album_id:
			r = dzrGet("/album/" + item)
			items.append(r)

		if len(items) > 1:
			items = map(standardize, items)
			return render_template('list.html', item=items, title=request.args.get('title', None))
		else:
			return render_template('album.html', album=items[0])
	else:
		return redirect("/auth")

@app.route('/label/<string:label_name>')
def label(label_name):
	"""
		Get all albums from a label
	"""
	if isAuth():
		items = dzrGet("/search/album?q=label:\"" + label_name + "\"")

		if len(items) > 1:
			items = map(standardize, items)
			
		return render_template('list.html', item=items, title=request.args.get('title', None))
	else:
		return redirect("/auth")

@app.route('/artist/<string:artist_id>')
def artist(artist_id):
	"""
		Artist page and list
	"""
	artist_id = artist_id.split(',')
	if isAuth():
		items = []
		for id in artist_id:
			r = dzrGet("/artist/" + id)
			items.append(r)

		if len(items) > 1:
			items = map(standardize, items)
			return render_template('list.html', item=items, title=request.args.get('title', None))
		else:
			artist = items[0]
			top_tracks = dzrGet("/artist/" + id + "/top", nb=5)
			artist['top_tracks'] = top_tracks
			return render_template('artist.html', artist=artist)
	else:
		return redirect("/auth")

@app.route('/artist/<string:artist_id>/<string:type>')
def artist_items(artist_id, type):
	"""
		Artist's methodes
	"""
	if isAuth():
		items = dzrGet("/artist/" + artist_id + "/" + type)

		items = map(standardize, items)
		
		if type == 'albums':
			# Add artist node to each album object
			artist = dzrGet("/artist/" + artist_id)
			for i in items:
				i['artist'] = artist

		return render_template('list.html', item=items, title=request.args.get('title', None))
	else:
		return redirect("/auth")

@app.route('/user/<string:user_id>')
def user(user_id):
	"""
		User summary
	"""
	if isAuth("basic_access", "listening_history"):
		r = dzrGet("/user/" + user_id)

		if user_id == session['id']:
			# compute average rank based on listening history
			history = dzrGet("/user/" + user_id + "/history")
			rank = []
			for row in history:
				if isinstance(row['rank'], int):
					rank.append(row['rank'])
			avg_rank = sum(rank)/len(rank)
		else:
			avg_rank = 0

		return render_template('user.html', user=r, rank=avg_rank)
	else:
		return redirect("/auth?perms=basic_access,listening_history")

@app.route('/user/<string:user_id>/<string:type>')
def user_items(user_id, type):
	"""
		User's faved content
	"""
	if isAuth():
		# Request special permission for the Listening History page
		if type == "history" and not isAuth("listening_history"):
			return redirect("/auth?perms=listening_history")

		items = dzrGet("/user/" + user_id + "/" + type)
		items = map(standardize, items)
		# reverse item list order for albums, artists, playlists and user charts
		items = list(reversed(items)) if type in ['artists', 'albums', 'playlists', 'tracks'] else items	

		return render_template('list.html', item=items, title=request.args.get('title', None))
	else:
		return redirect("/auth")

@app.route('/user/<string:user_id>/recommendations/<string:type>')
def user_recommendations(user_id, type):
	"""
		User's recommended content
	"""
	if isAuth():
		items = dzrGet("/user/" + user_id + "/recommendations/" + type)
		items = map(standardize, items)

		return render_template('list.html', item=items, title=request.args.get('title', None))
	else:
		return redirect("/auth")

@app.route('/clearcache')
def clearcache():
	"""
		TO DO: make this work.. :)
	"""
	if cache is not None:
		cache.clear()
	return redirect("/")

@app.route('/shutdown')
def shutdown():
	"""
		Route to shutdown the server
	"""
	func = request.environ.get('werkzeug.server.shutdown')
	if func is None:
		raise RuntimeError('Not running with the Werkzeug Server')
	func()
	return 'Server shutting down...'
	

def isAuth(*args):
	"""
		Check if user is authenticated with a valid token. Else redirect to auth
	"""
	if ('token' in session) & ('id' in session) & ('perms' in session):
		if (session['expire'] > time.time()) or (session['expire'] == 0):
			if len(args) > 0:
				for arg in args:
					if arg not in session['perms']:
						session.clear()
						session['redirect'] = request.full_path
						return False
			return True
	session.clear()
	session['redirect'] = request.full_path
	return False

def standardize(obj):
	"""
		Take any Deezer obj and return a standard object (e.g. artist or author keys are renammed as creator)
	"""
	if 'picture_medium' in obj.keys():
		obj['image'] = obj.pop('picture_medium')
	if 'cover_medium' in obj.keys():
		obj['image'] = obj.pop('cover_medium')
	return obj

def dzrGet(endpoint, **kwargs):
	"""
		Query a Deezer API endpoint with the proper parameter and output a clean response object
	"""
	query = "https://api.deezer.com" + str(endpoint) + "?access_token=" + session['token']

	param = {
		'limit': 2000,
		'nb': 10000,
		'cache': True
	}

	# If user passed some params, overwrite the default params
	if kwargs is not None:
		for key, value in kwargs.iteritems():
			param[key] = value

		if param['nb'] < param['limit']:
			param['limit'] = param['nb']

	# Add params to url
	for key, value in param.iteritems():
		query += "&" + key + "=" + str(value)

	r = get_cached(query).json() if param['cache'] == True else requests.get(query).json()
	response = r['data'] if 'data' in r.keys() else r

	# keep on fetching items until the last page is reached
	if 'next' in r.keys():
		while ('next' in r.keys()) & (int(param['nb']) > len(response)):
			r = get_cached(r['next']).json() if param['cache'] == True else requests.get(r['next']).json()
			response += r['data'] if 'data' in r.keys() else r

	return response

def memoize(func):
	"""
		Cache wrapper function
	"""
	cache = dict()
	
	def memoized_func(*args):
		if args in cache:
			if (time.time() - cache[args]['insert_date']) < CONFIG['CACHE_DURATION']:
				return cache[args]['result']
		
		result = func(*args)
		cache[args] = {
			'result': result,
			'insert_date': time.time()
		}

		return result

	return memoized_func

get_cached = memoize(requests.get)

app.secret_key = os.urandom(24)

if __name__ == '__main__':
    app.run(host=CONFIG['IP'], port=CONFIG['PORT'], debug=CONFIG['DEBUG'])