from abc import ABC, abstractmethod
from dataclasses import dataclass
from dataclasses_json import dataclass_json
import requests
import logging


class MonitorEntry(ABC):
    def __init__(self, json_dict):
        self.json_config = self.dict_to_config(json_dict)
        self.monitored_metric = None
        self.interval = self.json_config.interval

    @abstractmethod
    def dict_to_config(self, json_dict):
        pass

    @abstractmethod
    def pull_data(self):
        pass

    @abstractmethod
    def metric_str(self):
        pass

    def notification_str(self) -> str:
        if self.json_config.greater_than and self.monitored_metric:
            if self.monitored_metric > self.json_config.greater_than:
                return self.metric_str() + " greater than " + f"{self.json_config.greater_than}"
        if self.json_config.less_than and self.monitored_metric:
            if self.monitored_metric < self.json_config.less_than:
                return self.metric_str() + " less than " + f"{self.json_config.less_than}"
        return ""

    def status_str(self):
        if self.monitored_metric:
            return self.metric_str() + " is " + "{:.7f}".format(self.monitored_metric)
        else:
            return self.metric_str() + " is " + "unavailable"


@dataclass_json
@dataclass
class BinanceJsonConfig:
    type: str
    symbol: str
    greater_than:  float = None
    less_than: float = None
    interval: int = 3600


class BinanceEntry(MonitorEntry):
    NUM_RETRY = 10
    def dict_to_config(self, json_dict) -> BinanceJsonConfig:
        return BinanceJsonConfig.from_dict(json_dict)

    def metric_str(self):
        return "Binance " + self.json_config.type + " for " + self.json_config.symbol

    def pull_data(self):
        api_url = "https://fapi.binance.com/fapi/v1/fundingRate"
        params = {"symbol": self.json_config.symbol, "limit": 1}
        result = None
        for i in range(BinanceEntry.NUM_RETRY):
            try:
                response = requests.get(api_url, params=params)
                data = response.json()
                if data:
                    funding_rate = float(data[0]["fundingRate"])
                    result = funding_rate
                    break
                else:
                    logging.error("No data received from the API.")
            except Exception as e:
                logging.error(f"Error fetching data: {e}")
        self.monitored_metric = result
        return result


def entry_list_factory(json_dict):
    if json_dict["group"].lower() == "binance":
        entry_dict_list = json_dict["entries"]
        return [BinanceEntry(ed) for ed in entry_dict_list]
    else:
        return []
