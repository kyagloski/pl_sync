# pl_sync

depending on who you are, this may have a very niche use case, but for others, its very useful <br />
this script syncs all m3u playlist files (given the same file structure) in a directory with a subsonic server <br />
<br />
specifically it was meant to be used with Musicbee with the subsonic plugin (this plugin does not properly work so this is my solution currently) <br />
playlists can be statically mapped to a m3u file with musicbee and you can change the stored path layout in the playlist options <br />
once this is done just point the script to a the directory with the statically mapped m3u (or m3u8) and this script will push the changes to the subsonic server <br />
<br />
I also recommend making a seperate api_user on your subsonic server with absolutely no user privs, this ensures that if any account get breached by using this
script, it will just be a dummy account that has no access rights other than fucking with your playlists (which you should hopefully have backed up) <br />
<br />
dependencies: <br />
  xmltodict (for reading xml rest response from server) <br />
  requests (if you dont already have it, I cant remember if this is a standard python library) <br />
