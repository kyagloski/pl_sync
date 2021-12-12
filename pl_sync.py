#!/usr/bin/python3

import os, threading, time, copy
import requests
import xmltodict

query_types = {}
query_types["ping"] = "ping.view?"  
query_types["getPlaylist"] = "getPlaylist.view?"
query_types["getPlaylists"] = "getPlaylists.view?"    
query_types["createPlaylist"] = "createPlaylist.view?" 
query_types["deletePlaylist"] = "deletePlaylist.view?"
query_types["getSong"] = "getSong.view?"

DEBUG = 0
GET_OUTPUT = 1 # if true get requests are printed


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
                    query += ("&" + i + "=" + j)
            else:
                query += ("&" + i + "=" + query_args[i]) 
    if GET_OUTPUT: print("sending query at: ", query)
    response = requests.get(query)
    dict_data = xmltodict.parse(response.content)
    return dict_data

def read_m3u(dir):
    # params: dir: the directory you want to read in
    #         dir_strip: optional, path that gets stripped off dir name (to match subsonic generated m3u8 exports)
    m3us = {} # format: file_name : file_object 
    playlists = {} # format: playlist_name : song_array
    global directory_offset # yeah i know, i know, im not proud of it
    try: # path is a file
        f = open(dir)
        f_name = os.path.basename(f.name) # file name
        if "m3u" in f_name[-4:]: # check if file is m3u or m3u8
            m3us[f_name.split('.')[0]] = f
        #else: print("incorrect file type:\n ↳ " + f_name); return
    except: # path is a directory
        for i in os.listdir(dir):
            f = open(dir + i)
            f_name = os.path.basename(f.name) # file name
            if "m3u" in f_name[-4:]: # check if file is m3u or m3u8
                m3us[f_name.split('.')[0]] = f
            #else: print("incorrect file type:\n ↳ " + f_name + " → skipping...")
    for i in m3us:
        playlists[i] = []
        for j in m3us[i]:
            j = j.strip()
            if j == "#EXTM3U": # skip header
                continue
            playlists[i].append(j[len(directory_offset)::])
    return playlists

def get_args_ini():
    server_domain, api_user_name, api_user_pass, playlist_dir, directory_offset = "", "", "", "", ""
    f = open("pl_sync.ini")
    for i in f:
        if '[pl_sync_args]' in i: continue
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
        print(" ↳ " + dict_data['subsonic-response']['error']['@message'])
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
        #print("get_playlist_id error: \n ↳ cannot find playlist")
        return None  

def del_playlist(playlist_name):
    # params: playlist_name: str playlist name to be deleted
    pl_id = get_playlist_id(playlist_name) 
    if pl_id: # playlist under that name exists
        dict_data = basic_get(query_types["deletePlaylist"], {"id":str(pl_id)})
    else:
        print("del_playlist error:\n ↳ playlist does not exist")
    return dict_data

def get_all_songs(song_dict):
    error_count = 0
    song_id = 0
    print("> spinning thread for: all songs")
    print("> temporarily disabling get_output to reduce terminal spam")
    global GET_OUTPUT
    GET_OUTPUT = 0
    while error_count <= 5:
        dict_data = basic_get(query_types["getSong"], {"id": str(song_id)})
        if dict_data["subsonic-response"]["@status"] == "failed":
            error_count += 1
        else:
            error_count = 0
            song_dict[dict_data["subsonic-response"]["song"]["@path"]] = str(song_id)
        song_id += 1
    print("> finished gathering all songs")
    GET_OUTPUT = 1
    return song_dict

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
                if j in i: # this really should be an == but, for some reason that does not work
                    song_update_ids.append(master_song_list[j])
                    error_list.remove(i)
        for i in error_list:
            print("> cannot find song: ", i)
        if pl_id != None: # playlist exists, update it
            dict_data = basic_get(query_types["createPlaylist"], {"playlistId": pl_id, 
                                                                "name": playlist_name,
                                                                "songId": song_update_ids})
        else: # playlist does not exists, make new one
            dict_data = basic_get(query_types["createPlaylist"], {"name": playlist_name, "songId": song_update_ids})
        if dict_data['subsonic-response']['@status'] != "ok":
            print("updatePlaylist error: \n ↳ ", dict_data['subsonic-response']['error']['@message'])
    print("> syncing completed!")


if __name__ == "__main__":
    if DEBUG == 0:
        # gather data
        global server_domain, api_user_name, api_user_pass, playlist_dir, directory_offset # im lazy, sue me (actually dont)  
        global master_song_list          
        server_domain, api_user_name, api_user_pass, playlist_dir, directory_offset = get_args_ini()  
        master_song_list = get_all_songs({}) # get all songs in background as first task (it takes a few seconds)
        # execute order 66
        sync_playlists(playlist_dir)
    else:
        pass

