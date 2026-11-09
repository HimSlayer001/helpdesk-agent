# VPN access (GlobalConnect)

All remote work on internal systems requires the corporate VPN client, GlobalConnect.

## Installing the client
Download GlobalConnect from the Self-Service portal. On macOS, allow the system extension under System Settings > Privacy & Security after install. On Windows, the installer needs local admin rights; raise a ticket if you do not have them.

## Connecting
Use the portal address vpn.example-corp.com and sign in with your SSO username. You will be asked to approve an MFA push on your phone.

## Common errors
- "Gateway not responding": check your internet connection, then switch to the backup gateway vpn2.example-corp.com.
- "Certificate error": your device certificate has expired. Re-enrol the device from the Self-Service portal.
- Connected but internal sites do not load: disconnect, clear the DNS cache (macOS: `sudo dscacheutil -flushcache`), and reconnect.
