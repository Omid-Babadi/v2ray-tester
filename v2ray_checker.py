# V2Ray Config Checker
#
# Author: Jules @ AI
# Date: 2024-03-08
#
# Description:
# This script prompts the user to paste a V2Ray configuration (either a
# vmess:// link or a full JSON configuration). It then parses the configuration,
# extracts key details, displays them, and performs a basic TCP connectivity
# test (ping) to the server address and port.
#
# How to run:
# 1. Save this script as `v2ray_checker.py`.
# 2. Open a terminal or command prompt.
# 3. Navigate to the directory where you saved the script.
# 4. Run the script using Python: `python v2ray_checker.py`
# 5. When prompted, paste your V2Ray configuration into the terminal.
#    - For multi-line JSON, paste all lines.
#    - After pasting, press Ctrl+D (on Linux/macOS) or Ctrl+Z then Enter (on Windows)
#      to signal the end of input.
# 6. The script will then output the parsed information and connectivity test results.
#
# Requirements:
# - Python 3.x
#
# Note: This script performs a basic TCP ping and does not establish a full
# V2Ray connection. The "ping" is a measure of TCP handshake time.

import base64
import json
import socket
import time

def get_v2ray_config_from_user() -> str:
    """
    Prompts the user to paste their V2Ray configuration string.
    Allows for multi-line input.
    """
    print("Please paste your V2Ray configuration. Press Ctrl+D (or Ctrl+Z on Windows) then Enter when done:")
    lines = []
    while True:
        try:
            line = input()
            lines.append(line)
        except EOFError:
            break
    return "\n".join(lines)

def parse_v2ray_config(config_str: str) -> dict | None:
    """
    Parses a V2Ray configuration string.
    Handles both direct JSON and base64 encoded JSON (vmess://).
    """
    # Imports moved to the top of the file

    if config_str.startswith("vmess://"):
        try:
            decoded_str = base64.b64decode(config_str[8:]).decode('utf-8')
            config_json = json.loads(decoded_str)
            # Vmess links often have a slightly different structure,
            # we can try to normalize it or extract common fields.
            # For now, just return the parsed JSON.
            # Common fields: ps, add, port, id, aid, net, type, host, path, tls
            return config_json
        except Exception as e:
            print(f"Error decoding/parsing vmess link: {e}")
            return None
    else:
        try:
            # Attempt to parse as direct JSON
            config_json = json.loads(config_str)
            # Standard V2Ray JSON configs usually have an 'outbounds' array
            if "outbounds" in config_json and isinstance(config_json["outbounds"], list) and len(config_json["outbounds"]) > 0:
                # Assuming the first outbound is the primary one
                outbound_settings = config_json["outbounds"][0].get("settings", {}).get("vnext", [{}])[0]
                main_config = {
                    "ps": config_json["outbounds"][0].get("tag", "N/A"), # Use tag as name if available
                    "add": outbound_settings.get("address"),
                    "port": outbound_settings.get("port"),
                    "id": outbound_settings.get("users", [{}])[0].get("id"),
                    "aid": str(outbound_settings.get("users", [{}])[0].get("alterId", "0")),
                    "net": config_json["outbounds"][0].get("streamSettings", {}).get("network"),
                    "type": "N/A", # Often 'none' for header type in vmess
                    "host": config_json["outbounds"][0].get("streamSettings", {}).get("wsSettings", {}).get("headers", {}).get("Host") or \
                            config_json["outbounds"][0].get("streamSettings", {}).get("httpSettings", {}).get("host", [None])[0],
                    "path": config_json["outbounds"][0].get("streamSettings", {}).get("wsSettings", {}).get("path") or \
                            config_json["outbounds"][0].get("streamSettings", {}).get("httpSettings", {}).get("path"),
                    "tls": config_json["outbounds"][0].get("streamSettings", {}).get("security"),
                    "protocol": config_json["outbounds"][0].get("protocol")
                }
                # Add any other relevant top-level or stream settings
                stream_settings = config_json["outbounds"][0].get("streamSettings", {})
                if "tlsSettings" in stream_settings and stream_settings["tlsSettings"].get("serverName"):
                    main_config["sni"] = stream_settings["tlsSettings"]["serverName"]
                if "wsSettings" in stream_settings:
                    main_config["wsHeaders"] = stream_settings["wsSettings"].get("headers")

                return main_config
            else: # If not a full config, maybe it's a simpler JSON like vmess content
                 return config_json
        except json.JSONDecodeError:
            print("Configuration is not valid JSON.")
            return None
        except Exception as e:
            print(f"Error parsing JSON config: {e}")
            return None

if __name__ == "__main__":
    print("V2Ray Checker script initialized.")
    config_str = get_v2ray_config_from_user()
    if config_str:
        print("\nReceived configuration string.")
        # print(config_str) # No need to print the raw string now

        parsed_config = parse_v2ray_config(config_str)
        if parsed_config:
            print("\nParsed Configuration Details:")
            for key, value in parsed_config.items():
                print(f"  {key}: {value}")

            # Attempt to get address and port for ping test
            # This needs to be robust as field names can vary
            address = parsed_config.get("add") or parsed_config.get("address")
            port = parsed_config.get("port")

            if isinstance(port, str): # Port from vmess might be string
                try:
                    port = int(port)
                except ValueError:
                    print("Invalid port format in config.")
                    port = None

            if address and port:
                test_connectivity(address, port)
            else:
                print("\nCould not determine address and/or port from the config for connectivity test.")
        else:
            print("Failed to parse the configuration.")
    else:
        print("No configuration received.")

def test_connectivity(address: str, port: int, timeout: int = 3) -> None:
    """
    Tests basic TCP connectivity to the given address and port.
    Prints the result, including time taken if successful.
    """
    # Imports moved to the top of the file

    print(f"\nAttempting to connect to {address}:{port} (timeout: {timeout}s)...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        start_time = time.time()
        sock.connect((address, port))
        end_time = time.time()

        duration_ms = (end_time - start_time) * 1000
        print(f"Successfully connected to {address}:{port} in {duration_ms:.2f} ms.")

    except socket.timeout:
        print(f"Connection to {address}:{port} timed out after {timeout} seconds.")
    except socket.error as e:
        print(f"Connection to {address}:{port} failed: {e}")
    finally:
        if 'sock' in locals() and sock:
            sock.close()
