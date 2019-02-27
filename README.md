# deez.py

Deez.py is a Python **2** app using [Flask][1] to interact with the [Deezer][2] API.

Features included are
- Auth (retrieving a token for a given user)
- `/track/<id>`: display track information
- `/album/<id>`: display album information
- `/artist/<id>`: display artist information
- `/playlist/<id>`: display playlist information
- `/user/<id>`: display user information
- `/create/<playlist_name>`: create a playlist with the given name on the current user's profile
- `/update/<playlist_id>?tracks=<tracks_id>`: add the given tracks to the given playlist
- `/label/<label_name>`: show all albums released on the given label

Note: Most routes can take a comma-separated list of item ids (e.g. `/playlist/4262365542,1600104235`).

![Dashboard view](http://greird.webfactional.com/img/deezpy1.png "")

## Configuration

### 1. Deezer API configuration

Create a `config.cfg`, with the following lines, in the same repository as `deez.py`.
```
[deezer-api]
# Your deezer app settings
APP_ID=
APP_SECRET=

[flask-server]
# Flask server config
IP=127.0.0.1
PORT=5000
DEBUG=FALSE

[cache]
# Duration of the cache in seconds
DURATION=43200
```

To retrieve your APP_ID and APP_SECRET key you can create a new Deezer app here: https://developers.deezer.com/myapps/create
The only important fields are:
- `Domain`: Should be the same as your domain name or `127.0.0.1:5000` if deez.py is executed locally.
- `Redirect URL`: Should be the root url of the deez.py script + `/auth`. (e.g. `127.0.0.1:5000/auth`)

### 2. Install the required Python packages

```
pip install -r requirements.txt
```

### 3. Launch the app

Through the command line.
```
python deez.py
```

This will start a server on `127.0.0.1:5000` (locally) by default.
You can then open your browser and go to `127.0.0.1:5000` to use the app.

[1]: http://flask.pocoo.org
[2]: http://www.deezer.com