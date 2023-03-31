#!/usr/bin/env python3
import capnp
import copy
from dataclasses import dataclass, field
from functools import lru_cache
import struct
from typing import Dict, List, Optional, Set, Tuple

import panda.python.uds as uds

EcuType = Tuple[capnp.lib.capnp._EnumModule, int, Optional[int]]


def p16(val):
  return struct.pack("!H", val)


# TODO: import from common
def cache(user_function, /):
  return lru_cache(maxsize=None)(user_function)


class StdQueries:
  # FW queries
  TESTER_PRESENT_REQUEST = bytes([uds.SERVICE_TYPE.TESTER_PRESENT, 0x0])
  TESTER_PRESENT_RESPONSE = bytes([uds.SERVICE_TYPE.TESTER_PRESENT + 0x40, 0x0])

  SHORT_TESTER_PRESENT_REQUEST = bytes([uds.SERVICE_TYPE.TESTER_PRESENT])
  SHORT_TESTER_PRESENT_RESPONSE = bytes([uds.SERVICE_TYPE.TESTER_PRESENT + 0x40])

  DEFAULT_DIAGNOSTIC_REQUEST = bytes([uds.SERVICE_TYPE.DIAGNOSTIC_SESSION_CONTROL,
                                      uds.SESSION_TYPE.DEFAULT])
  DEFAULT_DIAGNOSTIC_RESPONSE = bytes([uds.SERVICE_TYPE.DIAGNOSTIC_SESSION_CONTROL + 0x40,
                                      uds.SESSION_TYPE.DEFAULT, 0x0, 0x32, 0x1, 0xf4])

  EXTENDED_DIAGNOSTIC_REQUEST = bytes([uds.SERVICE_TYPE.DIAGNOSTIC_SESSION_CONTROL,
                                       uds.SESSION_TYPE.EXTENDED_DIAGNOSTIC])
  EXTENDED_DIAGNOSTIC_RESPONSE = bytes([uds.SERVICE_TYPE.DIAGNOSTIC_SESSION_CONTROL + 0x40,
                                        uds.SESSION_TYPE.EXTENDED_DIAGNOSTIC, 0x0, 0x32, 0x1, 0xf4])

  MANUFACTURER_SOFTWARE_VERSION_REQUEST = bytes([uds.SERVICE_TYPE.READ_DATA_BY_IDENTIFIER]) + \
    p16(uds.DATA_IDENTIFIER_TYPE.VEHICLE_MANUFACTURER_ECU_SOFTWARE_NUMBER)
  MANUFACTURER_SOFTWARE_VERSION_RESPONSE = bytes([uds.SERVICE_TYPE.READ_DATA_BY_IDENTIFIER + 0x40]) + \
    p16(uds.DATA_IDENTIFIER_TYPE.VEHICLE_MANUFACTURER_ECU_SOFTWARE_NUMBER)

  UDS_VERSION_REQUEST = bytes([uds.SERVICE_TYPE.READ_DATA_BY_IDENTIFIER]) + \
    p16(uds.DATA_IDENTIFIER_TYPE.APPLICATION_SOFTWARE_IDENTIFICATION)
  UDS_VERSION_RESPONSE = bytes([uds.SERVICE_TYPE.READ_DATA_BY_IDENTIFIER + 0x40]) + \
    p16(uds.DATA_IDENTIFIER_TYPE.APPLICATION_SOFTWARE_IDENTIFICATION)

  OBD_VERSION_REQUEST = b'\x09\x04'
  OBD_VERSION_RESPONSE = b'\x49\x04'

  # VIN queries
  OBD_VIN_REQUEST = b'\x09\x02'
  OBD_VIN_RESPONSE = b'\x49\x02\x01'

  UDS_VIN_REQUEST = bytes([uds.SERVICE_TYPE.READ_DATA_BY_IDENTIFIER]) + p16(uds.DATA_IDENTIFIER_TYPE.VIN)
  UDS_VIN_RESPONSE = bytes([uds.SERVICE_TYPE.READ_DATA_BY_IDENTIFIER + 0x40]) + p16(uds.DATA_IDENTIFIER_TYPE.VIN)


@dataclass
class Request:
  request: List[bytes]
  response: List[bytes]
  whitelist_ecus: List[int] = field(default_factory=list)
  rx_offset: int = 0x8
  bus: int = 1
  # Whether this query should be run on the first auxiliary panda (CAN FD cars for example)
  auxiliary: bool = False
  # FW responses from these queries will not be used for fingerprinting
  logging: bool = False
  # boardd toggles OBD multiplexing on/off as needed
  obd_multiplexing: bool = True


@dataclass
class FwQueryConfig:
  requests: List[Request]
  # TODO: make this automatic and remove hardcoded lists, or do fingerprinting with ecus
  # Overrides and removes from essential ecus for specific models and ecus (exact matching)
  non_essential_ecus: Dict[capnp.lib.capnp._EnumModule, List[str]] = field(default_factory=dict)
  # Ecus added for data collection, not to be fingerprinted on
  extra_ecus: List[EcuType] = field(default_factory=list)
  fw_versions: Dict[str, Dict[EcuType, List[bytes]]] = field(default_factory=dict)

  def get_ecu_type(self, addr: int, sub_addr: Optional[int]) -> capnp.lib.capnp._EnumModule:
    for fw in self.fw_versions.values():
      for ecu_type, _addr, _sub_addr in fw:
        if (addr, sub_addr) == (_addr, _sub_addr):
          return ecu_type



  @property
  @cache
  def all_addrs(self) -> Set[Tuple[int, Optional[int]]]:
    # Add ecus in database + extra ecus to match against
    addrs = {(addr, sub_addr) for _, addr, sub_addr in self.extra_ecus}
    for fw in self.fw_versions.values():
      addrs |= {(addr, sub_addr) for _, addr, sub_addr in fw.keys()}
    return addrs

  def __post_init__(self):
    # Create auxiliary requests
    for i in range(len(self.requests)):
      if self.requests[i].auxiliary:
        new_request = copy.deepcopy(self.requests[i])
        new_request.bus += 4
        self.requests.append(new_request)

    self.addrs = []
    self.parallel_addrs = []
    self.ecu_types = {}

    for fw in self.fw_versions.values():
      for ecu_type, addr, sub_addr in list(fw) + self.extra_ecus:
        a = (addr, sub_addr)
        self.ecu_types[a] = ecu_type

        if sub_addr is None:
          if a not in self.parallel_addrs:
            self.parallel_addrs.append(a)
        else:
          if [a] not in self.addrs:
            self.addrs.append([a])

    self.addrs.insert(0, self.parallel_addrs)
