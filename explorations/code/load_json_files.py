import json
import glob
import os
import pandas as pd

# def load_json_files(folder="."):
#     """Match script exactly: dict[str, DataFrame] like {'Playlist1.json': df}"""
#     alljsons = sorted(glob.glob(os.path.join(folder, "*.json"), recursive=True))
#     json_data = {}
    
#     for f in alljsons:
#         try:
#             data = json.load(open(f, encoding="utf-8"))
#             if isinstance(data, list):
#                 json_data[f] = pd.DataFrame(data)
#             elif isinstance(data, dict):
#                 if "tracks" in data:
#                     json_data[f] = pd.json_normalize(data["tracks"])
#                 elif "playlists" in data:
#                     json_data[f] = pd.json_normalize(data["playlists"])
#                 else:
#                     json_data[f] = pd.DataFrame([data])
#             else:
#                 json_data[f] = pd.DataFrame([data])
#         except:
#             pass  # Skip errors
    
#     print("Loaded files:", list(json_data.keys()))
#     return json_data

# def load_json_files(folder="."):
#     all_jsons = glob.glob(os.path.join(folder, "*.json"))
#     streaming_files = [f for f in all_jsons if "Audio" in os.path.basename(f)]
#     other_files = [f for f in all_jsons if "Audio" not in os.path.basename(f)]
    
#     # Streams DataFrame (unchanged)
#     all_streams = []
#     for f in streaming_files:
#         all_streams.extend(json.load(open(f, 'r', encoding='utf-8')))
    
#     data = {'StreamingHistory': pd.DataFrame(all_streams)}  # Key 0
    
#     # Other files: Raw JSON (key = filename), NO normalize!
#     for f in other_files:
#         filename = os.path.basename(f)
#         raw = json.load(open(f, 'r', encoding='utf-8'))
#         data[filename] = raw  # Raw! {'playlists': [...]} for Playlist1.json
    
#     print(f"Loaded files: {list(data.keys())}")
#     return data  # Single dict, script unchanged!

def load_json_files(folder="."):
    all_jsons = glob.glob(os.path.join(folder, "*.json"))
    data = {}
    
    for f in all_jsons:
        filename = os.path.basename(f)
        raw = json.load(open(f, 'r', encoding='utf-8'))
        
        # Streams → DataFrame, others → raw
        if 'Streaming_History' in filename and 'Audio' in filename:
            data[filename] = pd.DataFrame(raw)
        else:
            data[filename] = raw  # Raw dict/list
    
    print(f"Loaded {len(data)} files:")
    for k in data:
        if isinstance(data[k], pd.DataFrame):
            print(f"  {k}: {len(data[k])} rows (DF)")
        else:
            print(f"  {k}: raw {type(data[k])}")
    
    return data

