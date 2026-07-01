"""PFSense Functions"""
import requests
import json
import ipaddress
from datetime import datetime, time, timezone
from classes import Log
import os
import re

class PfsenseFunction:
    """Class for pfSense functions."""
    # Cerificate paths
    CERT_PATH = './certs/api_user.crt'
    CA_CERT_PATH = './certs/CA.crt'
    KEY_PATH = './certs/api_user.key'
    # A list of optional pfsense logs

    def __init__(self, pfsense_init):
        """Initialize the pfSense function class."""
        self.log = Log.get_instance()
        self.url = pfsense_init.url
        self.api_key = pfsense_init.api_key
        self.ssl = pfsense_init.ssl
        self.verifycert = pfsense_init.verifycert
        self.default_interface = getattr(pfsense_init, 'default_interface', None)
        if self.default_interface is None and hasattr(pfsense_init, 'params'):
            cfg = pfsense_init.params.get('pfsense', {})
            self.default_interface = cfg.get('default_interface', 'wan')
        if not self.default_interface:
            self.default_interface = 'wan'

        # Lazy initialize the API
        self._api = None
        self._log_mgr = None
        self._rules = None
        self._interfaces = None
        self.log.debug(f"pfSense API initialized with the following parameters: {self.__dict__}")

    # Server Functions
    def _initialize_api_session(self):
        """Initialized the API session"""
        self._api = requests.Session()
        self._api.headers.update({
            'Authorization': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
            })
        if self.ssl and self.verifycert:
            # Log if the files exist
            if not os.path.isfile(self.CERT_PATH):
                self.log.error(f"Certificate file not found at {self.CERT_PATH}")
            if not os.path.isfile(self.CA_CERT_PATH):
                self.log.error(f"CA certificate file not found at {self.CA_CERT_PATH}")
            if not os.path.isfile(self.KEY_PATH):
                self.log.error(f"Private key file not found at {self.KEY_PATH}")        
            # Assign the cert and CA paths to the session
            self.cert = (self.CERT_PATH, self.KEY_PATH)
            self._api.cert = self.cert
            self._api.verify = self.CA_CERT_PATH
        else:
            self._api.verify = False

        self.log.debug(f"pfSense API session initialized.")

    def retrieve_certificate(self):
        """Retrieve the certificate from pfSense."""
        self.log.info(f"Retrieving certificate...")
        status, code, return_code, message, body =  self.get('api/v1/system/ca')
        
        refid = body[0].get('refid', None)
        description = body[0].get('descr', None)
        randomserial = body[0].get('randomserial', None)
        crt = body[0].get('crt', None)
        prv = body[0].get('prv', None)
        serial = body[0].get('serial', None)

        # Debugging
        self.log.debug_requests_function("PfsenseFunction", "retrieve_certificate", status, code, return_code, message, self.to_pretty(body))
        self.log.debug(f"PfsenseFunction.retrieve_certificate 'refid': {refid}")
        self.log.debug(f"PfsenseFunction.retrieve_certificate 'description': {description}")
        self.log.debug(f"PfsenseFunction.retrieve_certificate 'randomserial': {randomserial}")
        self.log.debug(f"PfsenseFunction.retrieve_certificate 'crt': {crt}")
        self.log.debug(f"PfsenseFunction.retrieve_certificate 'prv': {prv}")
        self.log.debug(f"PfsenseFunction.retrieve_certificate 'serial': {serial}")

        return refid, description, crt, prv, serial    
    
    def get_firewall_status(self):
        """Get the firewall status from pfSense."""
        self.log.info(f"Getting firewall status...")
        status, code, return_code, message, body =  self.get('api/v1/status/system')
        
        # Debugging 
        self.log.debug_requests_function("PfsenseFunction", "get_firewall_status", status, code, return_code, message, self.to_pretty(body))

        return body
    
    def _get_pfsense_interfaces(self):
        """Get a list of pfSense interfaces."""
        self.log.info(f"Getting pfSense interfaces...")
        interfaces = {}
        status, code, return_code, message, body =  self.get('api/v1/interface')
        
        # Debugging
        self.log.debug_requests_function("PfsenseFunction", "_get_pfsense_interfaces", status, code, return_code, message, self.to_pretty(body))
        for interface_name, metadata in body.items():
            interfaces[interface_name] = metadata
        # Debugging
        self.log.debug(f"Interfaces: {interfaces}")
        self.interfaces = interfaces

    # Requests Functions
    def _make_request(self, method, endpoint, data=None):
        url = f"{self.url}/{endpoint}"

        kwargs = {}  # Default to not verify SSL
        
        # Only add cert and verify if SSL and certificate verification are enabled
        if self.ssl and self.verifycert:
            kwargs['cert'] = (self.CERT_PATH, self.KEY_PATH)
            kwargs['verify'] = self.CA_CERT_PATH
        else:
            kwargs['verify'] = False

        try:
            if method.lower() == 'get':
                response = self.api.get(url, **kwargs)
            elif method.lower() == 'post':
                response = self.api.post(url, data=json.dumps(data), **kwargs)
            elif method.lower() == 'put':
                response = self.api.put(url, data=json.dumps(data), **kwargs)
            elif method.lower() == 'delete':
                response = self.api.delete(url, **kwargs)
            else:
                raise ValueError("Invalid HTTP method specified")

            self.log.debug(f"Request sent to URL: {url} with headers: {self.api.headers} and kwargs: {kwargs}")

            # Check if response is okay before parsing JSON
            if response.ok:
                # Send data to debugger
                # Get values from response attributes
                
                self.log.debug(f"PfsenseFunction._make_request 'response'.content: {response.content}")           
                return self._parse_response(response.json())
            else:
                self.log.error(f"Response error: {response.status_code} - {response.reason} - {response.text}")
                raise requests.exceptions.RequestException(f"Response error: {response.status_code} - {response.reason} - {response.text}")
        except requests.exceptions.RequestException as e:
            self.log.error(f"Request error: {e}")
            return None
        except ValueError as e:  # This will catch JSON decoding errors
            self.log.error(f"JSON Decode error: {e} - Response content: {response.content}")
            return None

    def _parse_response(self, response):
        """Parse a response from pfSense."""
        self.log.debug(f"Parsing response from server...")
        status = response.get('status')
        code = response.get('code')
        return_code = response.get('return_code')
        message = response.get('message')
        body = response.get('data')
        
        # Send data to debugger
        self.log.debug_requests_function("PfsenseFunction", "_parse_response", status, code, return_code, message, self.to_pretty(body))

        return status, code, return_code, message, body

    def get(self, endpoint):
        """Send a GET request to pfSense."""
        return self._make_request('GET', endpoint)
    
    def post(self, endpoint, data):
        """Send a POST request to pfSense."""
        return self._make_request('POST', endpoint, data)
    
    def put(self, endpoint, data):
        """Send a PUT request to pfSense."""
        return self._make_request('PUT', endpoint, data)

    def delete(self, endpoint):
        """Send a DELETE request to pfSense."""
        return self._make_request('DELETE', endpoint, data=None)
    
    # Firewall Rule Functions
    def _parse_firewall_body(self, data):
        """Parse the body of a firewall rule from pfSense."""
        self.rules = [FirewallRule(rule) for rule in data]

    def add_firewall_rule(self, src=None, src_port="any", dst="wan", dst_port="any", proto="any", direction="any", descr="PySOAR Generated Block Rule", rule_action="block", interface=None, gateway="", top=True):
        """Add firewall block/pass rules for one or more source addresses."""
        if src is None:
            src = ["any"]
        if interface is None:
            interface = getattr(self, 'default_interface', 'wan')
        if not isinstance(src, list):
            src = [src]

        added = 0
        last_message = ""
        for src_addr in src:
            if not self.is_ip_valid(src_addr):
                self.log.error(f"Invalid IP address: {src_addr}")
                continue
            if self.get_firewall_rule_by_ip(src_addr):
                self.log.info(f"IP address already blocked: {src_addr}")
                continue
            if rule_action == "block":
                stage_rule = FirewallRule.new_block_rule(
                    src_addr, src_port, dst, dst_port, proto, direction, descr, interface, gateway, top
                )
            else:
                stage_rule = FirewallRule.new_pass_rule(
                    src_addr, src_port, dst, dst_port, proto, direction, descr, interface, gateway, top
                )
            status, code, return_code, message, body = self.post('api/v1/firewall/rule', data=stage_rule)
            last_message = message
            self.log.debug_requests_function(
                "PfsenseFunction", "add_firewall_rule", status, code, return_code, message, self.to_pretty(body)
            )
            if status == "ok":
                added += 1

        if added == 0:
            if any(self.is_ip_valid(a) for a in src if a != "any"):
                self.log.info("All requested IPs were already blocked.")
                return True
            self.log.warning("No new firewall rules were added.")
            return False

        applied = self.apply_changes()
        self.log.info(f"Changes applied: {applied}; added {added} rule(s).")
        self.read_firewall_rule()
        return {"ip-dst": src, "pfsense-firewall-status": applied, "message": last_message}

    def apply_changes(self):
        """Apply changes to pfSense."""
        # Will reload all firewall items
        self.log.info(f"Applying changes...")
        status, code, return_code, message, body =  self.post('api/v1/firewall/apply', data={"async": True})
        self.log.debug_requests_function("PfsenseFunction", "apply_changes", status, code, return_code, message, self.to_pretty(body))
        
        if body:
            self.log.info(f"Changes applied successfully.")
            return True
        else:
            self.log.error(f"Error applying changes.")
            return False
    
    def read_firewall_rule(self):
        """Read a firewall rule from pfSense."""
        self.log.info(f"Reading firewall rules...")
        status, code, return_code, message, body = self.get('api/v1/firewall/rule')
        # Debugging
        self.log.debug_requests_function("PfsenseFunction", "read_firewall_rules", status, code, return_code, message, self.to_pretty(body))
        
        self._parse_firewall_body(body)

    def update_firewall_rule_cache(self):
        """Updates firewall rule cache  from pfSense."""
        # TODO: Add logic to update the firewall rule by pulling only the rules that have been updated since the last update
        self.log.debug(f"Updating firewall rules...")
        status, code, return_code, message, body = self.put('api/v1/firewall/rule', data=self.rules)
        # Debugging
        self.log.debug_requests_function("PfsenseFunction", "update_firewall_rules", status, code, return_code, message, self.to_pretty(body))

    def get_firewall_rule_by_description(self, description):
        """Get a firewall rule by description from pfSense."""
        self.log.info(f"Getting firewall rule by description: {description}...")
        if self.rules is None:
            self.read_firewall_rule()
        for rule in self.rules:
            if rule.description == description:
                return rule
        return None

    def get_firewall_rule_by_ip(self, ip):
        """Get a firewall rule by IP address from pfSense."""
        if self.rules is None:
            self.read_firewall_rule()
        for rule in self.rules:
            if rule.source_address and rule.destination_address:
                src_network = rule.source_address
                dst_network = rule.destination_address
                if self.is_in_network_range(ip, src_network) or self.is_in_network_range(ip, dst_network):
                    return rule
            elif rule.source_address:
                src_network = rule.source_address
                if self.is_in_network_range(ip, src_network):
                    return rule
            elif rule.destination_address:
                dst_network = rule.destination_address
                if self.is_in_network_range(ip, dst_network):
                    return rule
        return None
    
    def get_firewall_rule_by_port(self, port):
        """Get a firewall rule by port from pfSense."""
        if self.rules is None:
            self.read_firewall_rule()
        for rule in self.rules:
            if rule.source_port and rule.destination_port:
                src_port = rule.source_port
                dst_port = rule.destination_port
                if port == src_port or port == dst_port:
                    return rule
            elif rule.source_port:
                src_port = rule.source_port
                if port == src_port:
                    return rule
            elif rule.destination_port:
                dst_port = rule.destination_port
                if port == dst_port:
                    return rule
        return None 

    def delete_firewall_rule(self, tracker):
        """Delete a firewall rule from pfSense."""
        self.log.info(f"Deleting firewall rule {tracker}...")
        # Post the delete request
        status, code, return_code, message, body = self.delete(f"api/v1/firewall/rule", data={int(tracker)})
        
        # Debugging 
        self.log.debug_requests_function("PfsenseFunction", "delete_firewall_rule", status, code, return_code, message, self.to_pretty(body))

        # Verify the rule was deleted
        self.log.info(f"Verifying firewall rule {tracker} was deleted...")
        still_exists =  self.get_firewall_rule_by_tracker(tracker)
        if still_exists is None:
            self.log.info(f"Firewall rule {tracker} deleted successfully.")
            return True
        
    def get_firewall_rule_by_tracker(self, tracker):
        """Get a firewall rule by tracker from pfSense."""
        if self.rules is None:
            self.read_firewall_rule()
        # Parse Response
        for rule in self.rules:
            if rule.tracker == tracker:
                return rule
        return None
    
    def get_tracker_by_firewall_rule(self, rule_to_find):
        """Get a firewall rule by tracker from pfSense."""
        if self.rules is None:
            self.read_firewall_rule()
        # Parse Response
        for rule in self.rules:
            if rule == rule_to_find:
                # Debugging
                self.log.debug(f"PfsenseFunction.get_tracker_by_firewall_rule 'rule': {rule}")
                return rule.tracker
        return None
    
    # Log Manager Functions
    def get_logs(self, log_name):
        # Log name must be one of the following: config_history, dhcp, firewall, system
        # Log overview:
        # config_history: Read configuration history log
        # dhcp: Read DHCP log
        # firewall: Read firewall log
        # system: Read system log
        if log_name not in ['config_history', 'dhcp', 'firewall', 'system']:
            raise ValueError(f"Invalid log name: {log_name}")
        self.log.info(f"Getting {log_name} logs...")
        status, code, return_code, message, body = self.get(f"api/v1/status/log/{log_name}")

        # Debugging
        self.log.debug_requests_function("PfsenseFunction", "get_logs", status, code, return_code, message, self.to_pretty(body))

        return body
    
    def get_firewall_logs(self):
        """Get the firewall logs from pfSense."""
        if not self.log_mgr.system_logs:
            return self.log_mgr.gather_system_logs(self.get_logs('system'))
    
    def get_dhcp_logs(self):
        """Get the DHCP logs from pfSense."""
        if not self.log_mgr.dhcp_logs:
            return self.log_mgr.gather_dhcp_logs(self.get_logs('dhcp'))
    
    def get_system_logs(self):
        """Get the system logs from pfSense."""
        if not self.log_mgr.system_logs:
            return self.log_mgr.gather_system_logs(self.get_logs('system'))
    
    def get_config_history_logs(self):
        """Get the config history logs from pfSense."""
        if not self.log_mgr.config_history_logs:
            return self.log_mgr.gather_config_history_logs(self.get_logs('config_history'))
    
    def get_firewall_logs_by_datetimerange(self, start_date, end_date, start_time=None, end_time=None):
        """Calls the FirewallLog class to get the firewall logs by datetime range."""
        return self.log_mgr.get_firewall_logs_by_datetimerange(self.firewall_logs, start_date, end_date, start_time, end_time)

    def get_firewall_logs_by_daterange(self, start_date, end_date, start_time=None, end_time=None):
        """Playbook alias for get_firewall_logs_by_datetimerange."""
        return self.get_firewall_logs_by_datetimerange(start_date, end_date, start_time, end_time)
                
    def update_log_cache(self, log_name, interval=''):
        # TODO: Add logic to update the log cache from the PfsenseLog class based on a time interval
        pass 
    
    def is_in_network_range(self, ip, network_address):
        """Get a list of address ranges from pfSense."""
        try:
            network = ipaddress.ip_network(network_address, strict=False)
            return ipaddress.ip_address(ip) in network
        except ValueError as e:
            self.log.error(f"Invalid IP or CIDR: {e}")
            return False
        
    def is_ip_valid(self, ip):
        """Check if an IP address is valid."""
        # Determine if the IP address is a network address or a host address
        try:
            # Attempt to create an IP address object.
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            pass  # If it's not a valid IP address, we'll try if it's a network next.

        try:
            # Attempt to create an IP network object.
            ipaddress.ip_network(ip, strict=False)
            return True
        except ValueError as e:
            # If it's neither a valid IP address nor a network, it's invalid.
            self.log.error(f"Invalid IP address or network: {e}")
            return False

    @property 
    def api(self):
        """Lazy initialization of the API session"""
        if self._api is None:
            self._initialize_api_session()
        return self._api
    
    @property
    def rules(self):
        """Lazy initialization of the firewall rules"""
        if self._rules is None:
            self.read_firewall_rule()
        return self._rules

    @property
    def log_mgr(self):
        if not self._log_mgr:
            self._log_mgr = PfsenseLog()
        return self._log_mgr

    @property
    def interfaces(self):
        """Lazy initialization of the interfaces"""
        if self._interfaces is None:
            self._get_pfsense_interfaces()
        return self._interfaces

    @interfaces.setter
    def interfaces(self, interfaces):
        self._interfaces = interfaces
        
    @rules.setter
    def rules(self, rules):
        self._rules = rules

    @staticmethod
    def epoch_to_datetime(epoch_time, tz=timezone.utc):
        """Convert epoch time to a datetime object."""
        return datetime.fromtimestamp(epoch_time, tz=tz)
    
    @staticmethod
    def datetime_to_epoch(datetime_obj, tz=timezone.utc):
        """Convert a datetime object to epoch time."""
        return int(datetime_obj.replace(tzinfo=tz).timestamp())
        
    @staticmethod
    def to_pretty(json_data):
        """Make JSON pretty."""
        return json.dumps(json_data, indent=4, sort_keys=True)

class FirewallRule:
    """Formats Firewall Rules from pfSense."""
    def __init__(self, rule_data=None):
        self.log = Log.get_instance()
        self.rule_data = rule_data
        try:
            self.extract_rule_data()
        except Exception as e:
            self.log.error(f"Error extracting rule data: {e}")
            self.log.debug(f"FirewallRule.__init__ 'rule_data': {rule_data}")
    
    def extract_rule_data(self):
        # Safely get the value from rule_data or default to None if key does not exist
        #self.log.info(f"Extracting rule data...")
        self.id = self.rule_data.get("id")
        self.tracker = self.rule_data.get("tracker")
        self.type = self.rule_data.get("type")
        self.interface = self.rule_data.get("interface")
        self.ipproto = self.rule_data.get("ipprotocol")
        self.tag = self.rule_data.get("tag")
        self.tagged = self.rule_data.get("tagged")
        self.max = self.rule_data.get("max")
        self.max_src_nodes = self.rule_data.get("max-src-nodes")
        self.max_src_conn = self.rule_data.get("max-src-conn")
        self.max_src_states = self.rule_data.get("max-src-states")
        self.state_timeout = self.rule_data.get("statetimeout")
        self.state_type = self.rule_data.get("statetype")
        self.os = self.rule_data.get("os")
        self.protocol = self.rule_data.get("protocol")
        self.source = self.rule_data.get("source")
        self.destination = self.rule_data.get("destination")
        self.description = self.rule_data.get("descr")
        self.updated = self.rule_data.get("updated")
        self.created = self.rule_data.get("created")
        # Extract nested fields
        self.extract_addr_data()
        self.extract_time_data()

    def extract_addr_data(self):
        if self.source.get('address', None):
            self.source_address = self.source['address']
        if self.source.get('port', None):
            self.source_port = self.source['port']
        if self.source.get('network', None):
            self.source_network = self.source['network']
        if self.source.get('any', None):
            self.source_any = self.source['any']
        if self.destination.get('address', None):
            self.destination_address = self.destination['address']
        if self.destination.get('port', None):
            self.destination_port = self.destination['port']
        if self.destination.get('network', None):
            self.destination_network = self.destination['network']
        if self.destination.get('any', None):
            self.destination_any = self.destination['any']
        
    def extract_time_data(self):
        if self.updated.get('time', None):
            self.updated_time = self.updated['time']
        if self.updated.get('username', None):
            self.updated_username = self.updated['username']
        if self.created.get('time', None):
            self.created_time = self.created['time']
        if self.created.get('username', None):
            self.created_username = self.created['username']

    def format_rule(self):
        """Format the rule data."""
        return {
        "id": self.id,
        "tracker": self.tracker,
        "type": self.type,
        "interface": self.interface,
        "ipprotocol": self.ipproto,
        "tag": self.tag,
        "tagged": self.tagged,
        "max": self.max,
        "max-src-nodes": self.max_src_nodes,
        "max-src-conn": self.max_src_conn,
        "max-src-states": self.max_src_states,
        "statetimeout": self.state_timeout,
        "statetype": self.state_type,
        "os": self.os,
        "protocol": self.protocol,
        "source": self._format_source_addr_data(),
        "destination": self._format_destination_addr_data(),
        "descr": self.description,
        "updated": self._format_updated_time_data(),
        "created": self._format_created_time_data(),
    }
        
    @staticmethod
    def new_block_rule(
            self,
            src, 
            src_port, 
            dst, 
            dst_port, 
            proto="any", 
            direction="any", 
            descr="PySOAR Generated Pass Rule", 
            interface="wan", 
            gateway="", 
            top=True
            ):
        rule_action = "block"
        stage_rule = FirewallRule.rule_template(src, src_port, dst, dst_port, proto, direction, descr, rule_action, interface, gateway, top)
        return stage_rule
    
    @staticmethod
    def new_pass_rule(
            self, 
            src, 
            src_port, 
            dst, 
            dst_port, 
            proto="any", 
            direction="any", 
            descr="PySOAR Generated Pass Rule", 
            interface="wan", 
            gateway="", 
            top=True
            ):
        rule_action = "pass"
        stage_rule = FirewallRule.rule_template(src, src_port, dst, dst_port, proto, direction, descr, rule_action, interface, gateway, top)
        return stage_rule

    @staticmethod
    def rule_template(src, src_port, dst, dst_port, proto, direction, descr, rule_action, interface, gateway, top):
        # REF: "https://{PfSenseFunction.url}/api/documentation/#/Firewall%20>%20Rule/APIFirewallRuleCreate
        return {
            "ackqueue": "",
            "apply": True,
            "defaultqueue": "",
            "descr": descr,
            "direction": direction,
            "disabled": False,
            "dnpipe": "",
            "dst": dst, # Can be a single IP, a network CIDR, alias name, or interface
            "dstport": dst_port, # Can be a "any", a tcp or udp port (requires protocol to be set to tcp or udp)
            "floating": False,
            "gateway": gateway, # Name of an existing gateway traffic with route over upon match. Default '' indicated default gw
            "interface": [
                interface   # Descriptive name, the pfSense interface ID (e.g. wan, lan, optx), or the real interface ID
            ],
            "ipprotocol": "inet",
            "log": True,
            "pdnpipe": "",
            "protocol": proto, # Transfer protocol
            "quick": True, # If true, stop processing rules after this one matches
            "sched": "",
            "src": src,
            "srcport": src_port, # Can be a "any", a tcp or udp port (requires protocol to be set to tcp or udp)
            "statetype": "keep state", # keep state, sloppy state, synproxy state
            "tcpflags_any": True,   # Can specify a list of TCP flags to match using tcpflags1, tcpflags2, tcpflags_any 
            "top": False,       # If true, this rule will be placed at the top of the list
            "type": rule_action,   # block, pass, reject, match, or skeep
            }

    def _format_source_addr_data(self):
        """Formats the address data for the source."""
        data = {}
        if hasattr(self, 'source_address'):
            data['address'] = self.source_address
        if hasattr(self, 'source_port'):
            data['port'] = self.source_port
        if hasattr(self, 'source_network'):
            data['network'] = self.source_network
        if hasattr(self, 'source_any'):
            data['any'] = self.source_any
        self.log.debug(f"FirewallRule._format_source_addr_data 'data': {data}") # Debugging
        return data

    def _format_destination_addr_data(self):
        """Formats the address data for the destination."""
        data = {}
        if hasattr(self, 'destination_address'):
            data['address'] = self.destination_address
        if hasattr(self, 'destination_port'):
            data['port'] = self.destination_port
        if hasattr(self, 'destination_network'):
            data['network'] = self.destination_network
        if hasattr(self, 'destination_any'):
            data['any'] = self.destination_any
        self.log.debug(f"FirewallRule._format_destination_addr_data 'data': {data}")
        return data

    def _format_updated_time_data(self):
        """Formats the time data for the """
        return {
            "time": self.updated_time,
            "username": self.updated_username,
        }
    
    def _format_created_time_data(self):
        """Formats the time data for the """
        return {
            "time": self.created_time,
            "username": self.created_username,
        }        
    
class PfsenseLog:
    """Formats pfSense Logs."""
    def __init__(self):
        self._firewall_logs = None
        self._dhcp_logs = None
        self._system_logs = None
        self._config_history_logs = None
        # Debugging
        self.log = Log.get_instance()
        self.log.debug(f"FirewallLog.__init__: {self.__dict__}")

    def gather_firewall_logs(self, logs):
        """Converts each entry in a log list to a json object and then returns the list"""
        self.log.debug(f"Gathering firewall logs...")
        all_logs = []
        for log in logs:
            log = self.extract_log_data(log)
            # Convert the date (ex. 'Nov 7') and time (ex. 05:55:22) to a datetime object
            log['date'] = datetime.strptime(log['date'], '%b %d')
            log['time'] = datetime.strptime(log['time'], '%H:%M:%S')
            all_logs.append(log)
        
        self._firewall_log_data = all_logs
        return all_logs
    
    def get_firewall_logs_by_datetimerange(self, start_date, end_date, start_time=None, end_time=None):
        """Get the firewall logs by date and time range from pfSense."""
        # Ensure that the start_date and end_date are datetime.date objects
        self.log.debug("Getting firewall logs by date and time range...")

        # Convert dates and times into datetime for comparison
        start_datetime = datetime.combine(start_date, start_time if start_time else time.min)
        end_datetime = datetime.combine(end_date, end_time if end_time else time.max)

        # Ensure that the start_datetime is before the end_datetime
        if start_datetime >= end_datetime:
            raise ValueError("Start datetime must be before end datetime.")

        filtered_logs = [
            log for log in self._log_data
            if start_datetime <= datetime.combine(log['date'], log['time']) <= end_datetime
        ]

        return filtered_logs

    def extract_firewall_log_data(self, log_entry):
        """Parse a pfSense firewall log entry into a JSON object."""
        log_parts = [
            'date', 'time', 'hostname', 'process', 'rule_number', 'sub_rule_number',
            'anchor', 'tracker', 'interface', 'reason', 'action', 'direction',
            'ip_version', 'tos', 'ecn', 'ttl', 'id', 'offset', 'flags', 'proto',
            'length', 'src_ip', 'dest_ip', 'src_port', 'dest_port', 'data_length'
        ]

        # Regular expression to match the log entry pattern
        # Note: This pattern is very specific to the example log format provided
        pattern = r'(\w+\s+\d+\s+\d+:\d+:\d+)\s+(\w+)\s+(\w+)\[(\d+)\]:\s+(\d+),(\S*),(\S*),(\S*),(\S*),(\S*),(\S*),(\S*),(\S*),(\S*),(\S*),(\d+),(\S*),(\d+),(\S*),(\S*),(\S*),(\d+),(\S*),(\S*),(\S*),(\S*),(\d+),(\S+),(\d+),(\d+),(\d+)'

        # Match the log entry with the pattern
        match = re.match(pattern, log_entry)
        if match:
            # Extract the groups from the match and zip with the parts names
            log_data = dict(zip(log_parts, match.groups()))

            # Convert to JSON object (string)
            json_data = json.dumps(log_data, indent=4)
            return json_data
        else:
            self.log.error("Log entry does not match the expected format.")
            return None

    def gather_dhcp_logs(self, logs):
        """Converts each entry in a log list to a json object and then returns the list"""
        self._dhcp_log_data = logs

    def gather_system_logs(self, logs):
        """Converts each entry in a log list to a json object and then returns the list"""
        self._system_log_data = logs

    def gather_config_history_logs(self, logs):
        """Converts each entry in a log list to a json object and then returns the list"""
        self._config_history_log_data = logs
    
    @property
    def firewall_logs(self):
        return self._firewall_logs
    
    @property
    def dhcp_logs(self):
        return self._dhcp_logs
    
    @property
    def system_logs(self):
        return self._system_logs
    
    @property
    def config_history_logs(self):
        return self._config_history_logs

