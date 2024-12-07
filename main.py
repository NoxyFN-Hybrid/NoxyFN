import sys
import os
import semver
import survey
import aiohttp
import asyncio
import traceback
import json
import random
import winreg
import aiofiles
import psutil
import xml.etree.ElementTree as ET
from datetime import datetime
from rich import print_json
from console.utils import set_title
from mitmproxy.tools.web.master import WebMaster
from mitmproxy import http
from mitmproxy.options import Options
from pypresence import AioPresence

backendTypeMap = {
  "CID": "AthenaCharacter"
}

itemTypeMap = {
  "outfit": "AthenaCharacter",
  "backpack": "AthenaBackpack",
  "pickaxe": "AthenaPickaxe",
  "glider": "AthenaGlider",
  "contrail": "AthenaSkyDiveContrail",
  "shoes": "CosmeticShoes",
  "emote": "AthenaDance",
  "toy": "AthenaDance",
  "emoji": "AthenaDance",
  "pet": "AthenaPetCarrier",
  "spray": "AthenaDance",
  "music": "AthenaMusicPack",
  "bannertoken": "HomebaseBannerIcon",
  "wrap": "AthenaItemWrap",
  "loadingscreen": "AthenaLoadingScreen",
  "vehicle_wheel": "VehicleCosmetics_Wheel",
  "vehicle_wheel": "VehicleCosmetics_Wheel",
  "vehicle_skin": "VehicleCosmetics_Skin",
  "vehicle_booster": "VehicleCosmetics_Booster",
  "vehicle_body": "VehicleCosmetics_Body",
  "vehicle_drifttrail": "VehicleCosmetics_DrifTrail",
  "vehicle_cosmeticvariant": "CosmeticVariantToken",
  "cosmeticvariant": "none",
  "bundle": "AthenaBundle",
  "battlebus": "AthenaBattleBus",
  "itemaccess": "none",
  "sparks_microphone": "SparksMicrophone",
  "sparks_keyboard": "SparksKeyboard",
  "sparks_bass": "SparksBass",
  "sparks_drum": "SparksDrums",
  "sparks_guitar": "SparksGuitar",
  "sparks_aura": "SparksAura",
  "sparks_song": "SparksSong",
  "building_set": "JunoBuildingSet",
  "building_prop": "JunoBuildingProp",
}

def read_fortnite_game_data():
    with open('fortnite-game.json', 'r', encoding='utf-8') as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            raise ValueError("An error occured while decoding the game's data.")

def cls():
  os.system("cls" if os.name == "nt" else "clear")

def readConfig():
  with open("config.json") as f:
    config = json.loads(f.read())
    return config

def center(var: str, space: int | None = None):
  if not space:
    space = (
      os.get_terminal_size().columns
      - len(var.splitlines()[int(len(var.splitlines()) / 2)])
    ) // 2
  return "\n".join((" " * int(space)) + var for var in var.splitlines())

def processExists(name):
  for process in psutil.process_iter():
    try:
      if name.lower() in process.name().lower():
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
      pass
  return False

class Addon:
  def __init__(self, server: "MitmproxyServer"):
    self.server = server

  def request(self, flow: http.HTTPFlow) -> None:
    try:
      url = flow.request.pretty_url

      if "/v4/" in url:
        flow.request.url = "https://fngw-svc-gc-livefn.ol.epicgames.com/api/locker/v4/62a9473a2dca46b29ccf17577fcf42d7/account/cfd16ec54126497ca57485c1ee1987dc/active-loadout-group"

      if (
        "https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/game/v2/matchmakingservice/ticket/player"
        in flow.request.pretty_url
        and self.server.app.playlist
      ):
        playlistOld, playlistNew = list(self.server.app.playlistId.items())[0]
        flow.request.url = flow.request.url.replace(
          "%3A" + playlistOld, "%3A" + playlistNew
        )

  def response(self, flow: http.HTTPFlow):
    try:
      url = flow.request.pretty_url
      if (
        ("setloadoutshuffleenabled" in url.lower())
        or 
        url
        == 
        "https://fortnitewaitingroom-public-service-prod.ol.epicgames.com/waitingroom/api/waitingroom"
        or 
        "socialban/api/public/v1"
        in 
        url.lower()
      ):
        flow.response = http.Response.make(
          204,
          b"", 
          {"Content-Type": "text/html"}
        )
      
      if "putmodularcosmetic" in url.lower():
        presetMap = {
          "CosmeticLoadout:LoadoutSchema_Character":"character",
          "CosmeticLoadout:LoadoutSchema_Emotes": "emotes",
          "CosmeticLoadout:LoadoutSchema_Platform": "lobby",
          "CosmeticLoadout:LoadoutSchema_Wraps": "wraps",
          "CosmeticLoadout:LoadoutSchema_Jam": "jam",
          "CosmeticLoadout:LoadoutSchema_Sparks": "instruments",
          "CosmeticLoadout:LoadoutSchema_Vehicle": "sports",
          "CosmeticLoadout:LoadoutSchema_Vehicle_SUV": "suv",
        }
          
                
        baseBody = flow.request.get_text()
        body = json.loads(baseBody)
        loadoutData = json.loads(body['loadoutData'])
        
        if body.get('presetId') != 0:
          presetId = body['presetId']
          
          slots = loadoutData['slots']
          presetType = body['loadoutType']
          
          configTemplate = {
            "presetType": presetType,
            "presetId": presetId,
            "slots":  slots
          }
          
          with open("config.json") as f:
            data = json.load(f)
          
          key = presetMap.get(presetType)
          
          if data["saved"]['presets'][key].get(presetId):
            data["saved"]['presets'][key][presetId] = configTemplate
          else:
            data["saved"]['presets'][key].update({str(presetId):configTemplate})
          
          self.server.app.athena.update(
            {
              f"{presetType} {presetType}": {
                "attributes" : {
                  "display_name" : f"PRESET {presetId}",
                  "slots" : slots
                },
                "quantity" : 1,
                "templateId" : presetType
              },
            }
          )
          
          with open(
            "config.json",
            "w"
          ) as f:
            json.dump(data, f,indent=2)
          
        try:
          accountId = url.split("/")[8]
        except:
          accountId = "cfd16ec54126497ca57485c1ee1987dc"
            
        response = {
          "profileRevision": 99999,
          "profileId": "athena",
          "profileChangesBaseRevision": 99999,
          "profileCommandRevision": 99999,
          "profileChanges": [
            {
              "changeType": "fullProfileUpdate",
              "profile": {
                "created": "",
                "updated": str(datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'),
                "rvn": 0,
                "wipeNumber": 1,
                "accountId": accountId,
                "profileId": "athena",
                "version": "no_version",
                "items": self.server.app.athena,
                "stats": {
                  "loadout_presets": {
                    "CosmeticLoadout:LoadoutSchema_Character": {},
                    "CosmeticLoadout:LoadoutSchema_Emotes": {},
                    "CosmeticLoadout:LoadoutSchema_Platform": {},
                    "CosmeticLoadout:LoadoutSchema_Wraps": {},
                    "CosmeticLoadout:LoadoutSchema_Jam": {},
                    "CosmeticLoadout:LoadoutSchema_Sparks": {},
                    "CosmeticLoadout:LoadoutSchema_Vehicle": {},
                    "CosmeticLoadout:LoadoutSchema_Vehicle_SUV": {}
                  }
                },
                "commandRevision": 99999,
                "profileCommandRevision": 99999,
                "profileChangesBaseRevision": 99999
              }
            }
          ]
        }
        
        if body.get('presetId') != 0:
          response['profileChanges'][0]['profile']['stats']['loadout_presets'][presetType].update(
            {
              presetId: f"{presetType} {presetId}"
            }
          )

        flow.response = http.Response.make(
          200,
          json.dumps(response),
          {"Content-Type": "application/json"}
        )

      if url == "https://fortnitecontent-website-prod07.ol.epicgames.com/content/api/pages/fortnite-game/":
          try:
              fortnitegame_response = read_fortnite_game_data()
          except (FileNotFoundError, ValueError) as e:
              fortnitegame_response = {"error": str(e)}
          
          flow.response = http.Response.make(
              200,
              json.dumps(fortnitegame_response),
              {"Content-Type": "application/json"}
          )
          
      if"/SetItemFavoriteStatusBatch" in url:
        text = flow.request.get_text()
        favData = json.loads(text)
        
        changeValue = favData['itemFavStatus'][0]
        itemIds = favData['itemIds']
        
        if changeValue:
          with open("config.json") as f:
            data = json.load(f)
          
          for itemId in itemIds:
              if itemId not in data["saved"]["favorite"]:
                data["saved"]["favorite"].append(itemId)
              self.server.app.athena[itemId]["attributes"]['favorite'] = True

          with open("config.json", "w") as f:
            json.dump(data, f,indent=2) 
        else:   
          with open("config.json") as f:
            data = json.load(f)

          for itemId in itemIds:
              if itemId in data["saved"]["favorite"]:
                data["saved"]["favorite"].remove(itemId)
              self.server.app.athena[itemId]["attributes"]['favorite'] = False
          
          with open(
            "config.json",
            "w"
          ) as f:
            json.dump(data, f,indent=2)
        try:
          accountId = url.split("/")[8]
        except:
          accountId = "cfd16ec54126497ca57485c1ee1987dc"
        
        response = {
          "profileRevision": 99999,
          "profileId": "athena",
          "profileChangesBaseRevision": 99999,
          "profileCommandRevision": 99999,
          "profileChanges": [
            {
              "changeType": "fullProfileUpdate",
              "profile": {
                "created": "",
                "updated": str(datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'),
                "rvn": 0,
                "wipeNumber": 1,
                "accountId": accountId,
                "profileId": "athena",
                "version": "no_version",
                "items": self.server.app.athena,
                "commandRevision": 99999,
                "profileCommandRevision": 99999,
                "profileChangesBaseRevision": 99999
              }
            }
          ]
        }
        
        flow.response = http.Response.make(
          200,
          json.dumps(response),
          {"Content-Type": "application/json"}
        )
            
      if "/SetItemArchivedStatusBatch" in url:
        text = flow.request.get_text()
        archiveData = json.loads(text)
        
        changeValue = archiveData['archived']
        itemIds = archiveData['itemIds']
        
        if changeValue:
          
          data = readConfig()
            
          for itemId in itemIds:
              self.server.app.athena[itemId]["attributes"]['archived'] = True
              if itemId not in data['saved']['archived']:
                data["saved"]["archived"].append(itemId)
          
          with open(
            "config.json",
            "w"
          ) as f:
            json.dump(data, f,indent=2)
        else:
          
          with open("config.json") as f:
            data = json.load(f)
          
          for itemId in itemIds:
              self.server.app.athena[itemId]["attributes"]['archived'] = False
              if itemId not in data["saved"]["archived"]:
                data["saved"]["archived"].remove(itemId)
          
          with open(
            "config.json",
            "w"
          ) as f:
            json.dump(data,f,indent=2)    
        
        try:
          accountId = url.split("/")[8]
        except:
          accountId = "cfd16ec54126497ca57485c1ee1987dc"
          
        response = {
          "profileRevision": 99999,
          "profileId": "athena",
          "profileChangesBaseRevision": 99999,
          "profileCommandRevision": 99999,
          "profileChanges": [
            {
              "changeType": "fullProfileUpdate",
              "profile": {
                "created": "",
                "updated": str(datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'),
                "rvn": 0,
                "wipeNumber": 1,
                "accountId": accountId,
                "profileId": "athena",
                "version": "no_version",
                "items": self.server.app.athena,
                "commandRevision": 99999,
                "profileCommandRevision": 99999,
                "profileChangesBaseRevision": 99999
              }
            }
          ]
        }
        
        flow.response = http.Response.make(
          200,
          json.dumps(response),
          {"Content-Type": "application/json"}
        )      
      if "#setcosmeticlockerslot" in url.lower():
        try:
          accountId = url.split("/")[8]
        except:
          accountId = "cfd16ec54126497ca57485c1ee1987dc"
        
        baseBody = flow.request.get_text()
        reqbody = json.loads(baseBody)
        
        response = {
          "profileRevision": 99999,
          "profileId": "athena",
          "profileChangesBaseRevision": 99999,
          "profileCommandRevision": 99999,
          "profileChanges": [
            {
              "changeType": "fullProfileUpdate",
              "profile": {
                "created": "",
                "updated": str(datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'),
                "rvn": 0,
                "wipeNumber": 1,
                "accountId": accountId,
                "profileId": "athena",
                "version": "no_version",
                "items": self.server.app.athena,
                "commandRevision": 99999,
                "profileCommandRevision": 99999,
                "profileChangesBaseRevision": 99999
              }
            }
          ]
        } 
        flow.response = http.Response.make(
          200,
          json.dumps(response),
          {"Content-Type": "application/json"}
        )

      if  "client/QueryProfile?profileId=athena" in url or "client/QueryProfile?profileId=common_core" in url or "client/ClientQuestLogin?profileId=athena" in url:
        text = flow.response.get_text()
        athenaFinal = json.loads(text)
        try:
          athenaFinal["profileChanges"][0]["profile"]["items"].update(self.server.app.athena)
          if self.server.app.level:
            athenaFinal["profileChanges"][0]["profile"]["stats"]["attributes"]["level"] = self.server.app.level
          if self.server.app.battleStars:
            athenaFinal["profileChanges"][0]["profile"]["stats"]["attributes"]["battlestars"] = self.server.app.battleStars
          try:
            if self.server.app.crowns:
              athenaFinal["profileChanges"][0]["profile"]["items"]["VictoryCrown_defaultvictorycrown"]['attributes']['victory_crown_account_data']["total_royal_royales_achieved_count"] = self.server.app.crowns
          except KeyError:
            pass
          flow.response.text = json.dumps(athenaFinal)

      if url.startswith("https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/storeaccess/v1/request_access/"):
        accountId = url.split("/")[1:]
        flow.request.url = flow.request.url.replace(
          accountId,
          "cfd16ec54126497ca57485c1ee1987dc"
        )

      if "https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/matchmaking/session/" in url.lower() and "/join" in url.lower():
        flow.response = http.Response.make(
          200,
          b"[]",
          {"Content-Type": "application/json"}
        )

class MitmproxyServer:
  def __init__(
    self,
    app: "NoxyFN",
    loop: asyncio.AbstractEventLoop
  ):
    try:
      self.app = app
      self.loop = loop
      self.running = False
      self.task = None
      self.stopped = asyncio.Event()
      self.m = WebMaster(
        Options(),
        with_termlog=False
      )
      self.m.options.listen_host = "127.0.0.1"
      self.m.options.listen_port = 1942
      self.m.options.web_open_browser = False
      self.m.addons.add(Addon(self))
    except KeyboardInterrupt:
      pass

  def run_mitmproxy(self):
    self.running = True
    try:
      self.task = self.loop.create_task(self.m.run())
    except KeyboardInterrupt:
      pass

  def start(self):
    self.running = True
    try:
      self.run_mitmproxy()
    except TypeError:
      if self.task:
        self.task.cancel()
      self.task = None
      self.stopped.set()
      return self.stop()

class NoxyFN:
  def __init__(
    self,
    loop: asyncio.AbstractEventLoop | None=None,
  ):
    self.loop = loop or asyncio.get_event_loop()
    self.ProxyEnabled = False
    self.configFile = str = "config.json",
    self.mitmproxy_server = MitmproxyServer(
      app=self,
      loop=self.loop
    )

    self.config = {}

  async def __async_init__(self):
    try:
      async with aiofiles.open(self.configFile) as f:
        self.config = json.loads(await f.read())      
    except: 
      pass

    self.athena = await self.buildAthena()
    
  async def buildAthena(self):
    base = {}

    config = readConfig()
    async with aiohttp.ClientSession() as session:
      async with session.get(
        "https://fortniteapi.io/v2/items/list?fields=id,name,styles,type",
        headers={"Authorization": "f594c6d7-d4cd084a-dc3bd5f4-9def39da"},
      ) as request:
        FortniteItems = await request.json()
        GithubItems = await request.text()
        
    ThirdPartyItems = [item for item in GithubItems.split(";")]
    for Item in ThirdPartyItems:
      backendType = backendTypeMap.get(Item.split("_")[0])
      templateId = f"{backendType}:{Item}"

      variants = []

      itemTemplate = {
        templateId : {
          "templateId": templateId,
          "quantity": 1,
          "attributes": {
            "creation_time": None,
            "archived": True if templateId in config['saved']['archived'] else False,
            "favorite": True if templateId in config['saved']['favorite'] else False,
            "variants": variants,
            "item_seen": True,
            "giftFromAccountId": "cfd16ec54126497ca57485c1ee1987dc",
          },
        }
      }
      base.update(itemTemplate)

    for item in FortniteItems["items"]:

      variants = []
      
      if item.get("styles"):
        
        itemVariants = []
        variant = {}
        itemVariantChannels = {}
        
        for style in item['styles']:

          for styles in item["styles"]:
            styles['channel'] = styles['channel'].split(".")[-1]
            styles['tag'] = styles['tag'].split(".")[-1]
            
            channel = styles["channel"]
            channelName = styles["channelName"]
            
            if styles["channel"] not in variant:
              
              variant[channel] = {
                "channel": channel,
                "type": channelName,
                "options": []
              }
            
            
            variant[channel]["options"].append(
              {
                "tag": styles["tag"] ,
                "name": styles["name"],
              }
            )

          option = {
              "tag": styles["tag"],
              "name": styles["name"],
          }
          
          newStyle = list(variant.values())
          
          variantTemplate = {
            "channel": None,
            "active": None,
            "owned": []
          }
          variantFinal = newStyle[0]
          
          try:
            variantTemplate['channel'] = variantFinal['channel']
          except:
            continue
          
          variantTemplate['active'] = variantFinal['options'][0]['tag']
          
          for mat in variantFinal['options']:
            variantTemplate['owned'].append(mat['tag'])
            
          variants.append(variantTemplate)
      
      templateId = str(itemTypeMap.get(item["type"]["id"])) + ":" + str(item["id"])

      itemTemplate = {
          templateId : {
          "templateId": templateId,
          "quantity": 1,
          "attributes": {
            "creation_time": None,
            "archived": True if templateId in config['saved']['archived'] else False,
            "favorite": True if templateId in config['saved']['favorite'] else False,
            "variants": variants,
            "item_seen": True,
            "giftFromAccountId": "4735ce9132924caf8a5b17789b40f79c",
          },
        }
      }

      base.update(itemTemplate)
    
    extraTemplates = [
      {
        "VictoryCrown_defaultvictorycrown":
          {
            "templateId": "VictoryCrown:defaultvictorycrown",
            "attributes": {
              "victory_crown_account_data": {
                "has_victory_crown": True,
                "data_is_valid_for_mcp": True,
                "total_victory_crowns_bestowed_count": 500,
                "total_royal_royales_achieved_count": 1942
              },
              "max_level_bonus": 0,
              "level": 124,
              "item_seen": False,
              "xp": 0,
              "favorite": False
            },
            "quantity": 1
          }
      },
      {
        "Currency:MtxPurchased": {
          "templateId": "Currency:MtxPurchased",
          "attributes": {"platform": "EpicPC"},
          "quantity": 13500
        }
      }
    ]

    for template in extraTemplates:
      base.update(template)  

    config = readConfig()
    
    for presetType in config['saved']['presets'].values():
      for preset in presetType.values():
        base.update(
          {
            f"{preset['presetType']} {preset['presetId']}": {
              "attributes" : {
                "display_name" : f"PRESET {preset['presetId']}",
                "slots" : preset['slots']
              },
              "quantity" : 1,
              "templateId" : preset['presetType']
            },
          }
        )

    self.athena = base
    
    return base
  
  async def menu(self):
    while True:
      self.title()

      if self.running:
          self.mitmproxy_server.stop()
      else:
          try:
            self.mitmproxy_server.start()
            await self.mitmproxy_server.stopped.wait()
          except:
            self.running = False
            self.mitmproxy_server.stop()
  
  async def main(self):
    cls()
    await self.menu()

  async def run(self):
    try:
      await self.main()
    except KeyboardInterrupt:
      exit()

  @staticmethod
  async def new():
    cls = NoxyFN()
    await cls.__async_init__()
    return cls

if __name__ == "__main__":
  async def main():
    try:
      app = await NoxyFN.new()
      await app.run()
    except:
      print(traceback.format_exc())

  asyncio.run(main())
