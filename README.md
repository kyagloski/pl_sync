# pl_sync

depending on who you are this may have a very niche use case, but for others its very useful
this script syncs all m3u playlist files (given the same file structure) in a directory with a subsonic server

specifically it was meant to be used with Musicbee with the subsonic plugin (this plugin does not properly work so this is my solution currently)
playlists can be statically mapped to a m3u file with musicbee and you can change the stored path layout in the playlist options
once this is done just point the script to a the directory with the statically mapped m3u (or m3u8) and this script will push the changes to the subsonic server

dependencies:
  xmltodict (for reading xml rest response from server)
  requests (if you dont already have it, I cant remember if this is a standard python library)
