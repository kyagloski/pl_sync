#!/usr/bin/python3

import os, sys, pathlib
# required dependencies
import requests
import xmltodict

query_types = {}
query_types["ping"] = "ping.view?"  
query_types["getPlaylist"] = "getPlaylist.view?"
query_types["getPlaylists"] = "getPlaylists.view?"   
query_types["updatePlaylist"] = "updatePlaylist.view?" 
query_types["createPlaylist"] = "createPlaylist.view?"
query_types["deletePlaylist"] = "deletePlaylist.view?"
query_types["getIndexes"] = "getIndexes.view?"
query_types["getMusicDirectory"] = "getMusicDirectory.view?"
query_types["getSong"] = "getSong.view?"
 
DEBUG = 0


def basic_get(query_type, query_args=None):
    # params: query_type: found in query_types dict
    #         query_args: arguments for query type, not always required
    #                     more info here: http://www.subsonic.org/pages/api.jsp
    global server_domain, api_user_name, api_user_pass
    query = server_domain + query_type + "u=" + api_user_name + "&p=" + api_user_pass + "&v=1.16&c=pl_sync"
    if query_args != None:
        for i in query_args: # dictionary
            if type(query_args[i]) == list: # checks if val of dict key is list
                for j in query_args[i]:
                    query += ("&" + str(i) + "=" + str(j))
            else:
                query += ("&" + i + "=" + str(query_args[i]))
    if DEBUG: print(">> sending query at: ", query)
    response = requests.get(query)
    dict_data = xmltodict.parse(response.content)
    return dict_data

def read_m3u(dir):
    # params: dir: the directory you want to read in
    #         dir_strip: optional, path that gets stripped off dir name (to match subsonic generated m3u8 exports)
    m3us = {} # format: file_name : file_object 
    playlists = {} # format: playlist_name : song_array
    global directory_offset # yeah i know, i know, im not proud of it
    if dir == "": dir = str((pathlib.Path().absolute()) / "_")[:-1] # scan current directory if ini entry is empty
    try: # path is a file
        f = open(dir)
        print("> found playlist file:", dir)
        f_name = os.path.basename(f.name) # file name
        if "m3u" in f_name[-4:]: # check if file is m3u or m3u8
            m3us[f_name.split('.')[0]] = f
            print("> found playlist file:", dir)
        #else: print("incorrect file type:\n ??? " + f_name); return
    except: # path is a directory
        for i in os.listdir(dir):
            try: # not great
                f = open(dir + i)
            except:
                print(">> not attempting to open file or directory:", dir + i)
                continue
            f_name = os.path.basename(f.name) # file name
            if "m3u" in f_name[-4:]: # check if file is m3u or m3u8
                m3us[f_name.split('.')[0]] = f
                print("> found playlist file:", dir + i)
            #else: print("incorrect file type:\n ??? " + f_name + " ??? skipping...")
    for i in m3us:
        playlists[i] = []
        for j in m3us[i]:
            j = j.strip()
            if j == "#EXTM3U": continue # skip header
            playlists[i].append(j[len(directory_offset)::])
    return playlists

def get_args_ini():
    server_domain, api_user_name, api_user_pass, playlist_dir, directory_offset = "", "", "", "", ""
    try:
        f = open("pl_sync.ini")
    except:
        print(">> cannot find pl_sync.ini file \n>> exiting")
        quit()
    for i in f:
        if '[pl_sync_args]' in i or i[0] == ";": continue
        i = i.replace('"', "").replace("'", "").strip().split('=')
        if i[0] == 'server_domain': server_domain = i[1] + 'rest/'
        if i[0] == 'api_user_name': api_user_name = i[1]
        if i[0] == 'api_user_pass': api_user_pass = i[1]
        if i[0] == 'playlist_dir': playlist_dir = i[1]
        if i[0] == 'directory_offset': directory_offset = i[1]
    return server_domain, api_user_name, api_user_pass, playlist_dir, directory_offset

def get_playlist(id):
    # params: id: int id of playlist (1 start index)
    dict_data = basic_get(query_types["getPlaylist"], {"id":str(id)})
    if dict_data['subsonic-response']['@status'] == 'failed':
        print('get request failed: ')
        print(" ??? " + dict_data['subsonic-response']['error']['@message'])
        return 0
    stripped_dict = dict_data['subsonic-response']['playlist']['entry']
    songs_id = []
    songs_name = []
    for i in stripped_dict:
        songs_id.append(i["@id"])
        songs_name.append(i["@path"])
    playlist_ids = {dict_data['subsonic-response']['playlist']['@id'] : songs_id}
    playlist_name = {dict_data['subsonic-response']['playlist']['@name'] : songs_name}
    return playlist_ids, playlist_name

def get_playlist_id(name):
    # params: name: name of playlist (provided from m3u)
    dict_data = basic_get(query_types["getPlaylists"])
    name_id_dict = {}
    try:
        for i in dict_data['subsonic-response']['playlists']['playlist']:
            name_id_dict[i['@name']] = i['@id']
        for i in name_id_dict:
            if name == i:
                return name_id_dict[i]
    except:
        #print("get_playlist_id error: \n ??? cannot find playlist")
        return None  

def del_playlist(playlist_name):
    # params: playlist_name: str playlist name to be deleted
    pl_id = get_playlist_id(playlist_name) 
    if pl_id: # playlist under that name exists
        dict_data = basic_get(query_types["deletePlaylist"], {"id":str(pl_id)})
    else:
        print("del_playlist error:\n ??? playlist does not exist")
    return dict_data

def get_folder_data(id, music_dict):
    # oh shit, watch out boys this uses recursion
    # params: id: string folder index id
    dict_data = basic_get(query_types["getMusicDirectory"], {"id" : id})
    if dict_data["subsonic-response"]["@status"] == "failed" : print(">>> failed to get folder ids error: ", dict_data["subsonic-response"]["error"]['@message'])
    for i in dict_data["subsonic-response"]["directory"]["child"]:
        if i['@isDir'] == "true": get_folder_data(i["@id"], music_dict)
        else: music_dict[i["@path"]] = i["@id"]

def get_all_songs():
    base_folder_ids = []
    dict_data = basic_get(query_types["getIndexes"])
    for i in dict_data["subsonic-response"]["indexes"]["index"]:
        base_folder_ids.append(str(list(list(i.values())[1].values())[0]))
    music_dict = {}
    for i in base_folder_ids:
        get_folder_data(i, music_dict)
    return music_dict

def sync_playlists(playlist_dir):
    """
    uses newPlaylist to update old playlist with same id
    if a playlist is not found with the given name, a new one is created
    @params: playlist_name: name of playlist to update or create
             master_song_list: list of all songs to grab song ids from
    """
    m3u_pls = read_m3u(playlist_dir)
    for playlist_name in m3u_pls:
        pl_id = get_playlist_id(playlist_name)
        error_list = m3u_pls[playlist_name][:] # keeps track of what was not added to song_update_ids
        song_update_ids = []
        global master_song_list
        for i in m3u_pls[playlist_name]:
            for j in master_song_list:
                if j in i: # this really should be an ==, but for some reason that does not work
                    song_update_ids.append(master_song_list[j])
                    error_list.remove(i)
        for i in error_list:
            print("> cannot find song: ", i)
        if pl_id != None: # playlist exists, update it
            dict_data = basic_get(query_types["createPlaylist"], {"playlistId": pl_id, 
                                                                "name": playlist_name,
                                                                "songId": song_update_ids})
            dict_data1 = basic_get(query_types["updatePlaylist"], {"playlistId": get_playlist_id(playlist_name),
                                                                "public": "true"}) # make playlist public every time for redundancy
        else: # playlist does not exists, make new one
            dict_data = basic_get(query_types["createPlaylist"], {"name": playlist_name, "songId": song_update_ids})
            dict_data1 = basic_get(query_types["updatePlaylist"], {"playlistId": get_playlist_id(playlist_name),
                                                                "public": "true"}) # make playlist public
        if dict_data['subsonic-response']['@status'] != "ok":
            print("updatePlaylist error: \n ??? ", dict_data['subsonic-response']['error']['@message'])
    print("> syncing completed!")

def fix_playlists(playlist_dir):
    # attempts to reconstruct playlists in the case of a changing server file tree
    global master_song_list, directory_offset
    m3u_pls = read_m3u(playlist_dir)
    if playlist_dir == "": playlist_dir = "."
    for playlist in m3u_pls:
        updated_playlist = {}
        for song in m3u_pls[playlist]:
            for i in master_song_list:
                if song.split(song[0])[-1] in i:
                    updated_playlist[i] = master_song_list[i]
        filename = playlist + ".m3u.new"
        f = open(filename, "a")
        for i in updated_playlist:
            f.write(directory_offset + "/" + i + '\n')
        f.close()
        os.rename((playlist + ".m3u"), (playlist + ".m3u.old"))
        os.rename((playlist + ".m3u.new"), (playlist + ".m3u"))

def print_help():

    pass

# TODO: ini wizard to help user make ini file that suits them
if __name__ == "__main__":
    normal_run = 1
    global server_domain, api_user_name, api_user_pass, playlist_dir, directory_offset # im lazy, sue me (actually dont)  
    global master_song_list
    server_domain, api_user_name, api_user_pass, playlist_dir, directory_offset = get_args_ini()  
    master_song_list = get_all_songs() # gather data
    if normal_run:
        try:
            if sys.argv[1] in ['fix', '-f', '-fix']: fix_playlists(playlist_dir)
            elif sys.argv[1] in ['help', '-h', '-help']: print_help()
        except Exception as e:
            # execute order 66
            sync_playlists(playlist_dir)
        
    else:
        pass

