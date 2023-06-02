from pytapo import Tapo
from pytapo.media_stream.downloader import Downloader
import asyncio
import os
from datetime import datetime
import json
from glob import glob
from dataclasses import dataclass
from dataclasses_json import dataclass_json

# Directory where the Json config is stored
CONFIG_DIR = "./configs/"


@dataclass_json
@dataclass
class TapoConfig:
    outputRootDir: str = "./output"
    deviceType: str = "TAPO.HUB"
    host: str = ""
    user: str = "admin"
    password: str = ""
    cloudPassword: str = ""
    superSecretKey: str = ""
    playerID: str = ""
    windowSize: int = 50

    def setOutputDirectory(self, alias_name):
        self.outputDir = os.path.join(
            self.outputRootDir,
            alias_name,
        )
        return self.outputDir


async def download_async_by_date(tapo_camera: Tapo, date: str, config: TapoConfig):
    # Get list to download
    recordings = tapo_camera.getRecordings(date)
    for recording in recordings:
        for key in recording:
            downloader = Downloader(
                tapo_camera,
                recording[key]["startTime"],
                recording[key]["endTime"],
                config.outputDir,
                None,
                False,
                config.windowSize,
                fileName=f"{datetime.fromtimestamp(int(recording[key]['startTime'])).strftime('%Y-%m-%d %H_%M_%S')}.mp4",
            )
            async for status in downloader.download():
                statusString = status["currentAction"] + " " + status["fileName"]
                if status["progress"] > 0:
                    statusString += (
                        ": "
                        + str(round(status["progress"], 2))
                        + " / "
                        + str(status["total"])
                    )
                else:
                    statusString += "..."
                print(
                    statusString + (" " * 10) + "\r",
                    end="",
                )
            print("")


async def download_async(tapo_camera: Tapo, config: TapoConfig):
    print("Getting recordings...")
    recordings_date = tapo_camera.getRecordingsList()

    recordings_date_list = [
        v["date"]
        for search_results in recordings_date
        for _, v in search_results.items()
    ]

    for date in recordings_date_list:
        await download_async_by_date(tapo_camera, date, config)


def exec_download(config: TapoConfig):
    # Connecting H200 Hub
    print("Connecting to Hub...")
    tapo_hub = Tapo(
        config.host, config.user, config.cloudPassword, config.cloudPassword
    )

    # Get Child Camera Devices
    for d in tapo_hub.getChildDevices():
        if not d.get("device_model") in ["C400", "C420"]:
            print(f"{d.get('device_model')} is not supported.")
            continue
        child_device_id = d["device_id"]
        device_alias = d["alias"]

        print(f"{device_alias} : {child_device_id}")
        tapo_camera = Tapo(
            config.host,
            config.user,
            config.cloudPassword,
            config.cloudPassword,
            childID=child_device_id,
            playerID=config.playerID,
        )
        output_dir = config.setOutputDirectory(device_alias)
        os.makedirs(output_dir, exist_ok=True)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(download_async(tapo_camera, config))


if __name__ == "__main__":
    config_files = glob(os.path.join(CONFIG_DIR, "*.json"))
    for config_file in config_files:
        with open(config_file) as f:
            config = TapoConfig.from_dict(json.load(f))
        exec_download(config)
