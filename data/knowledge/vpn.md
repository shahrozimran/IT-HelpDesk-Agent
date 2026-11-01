# Remote-access VPN guide

SYNTHETIC TRAINING DOCUMENT. Version 2026-11-01. This guide describes the fictional Campus-Lab VPN for an educational simulation. It supplies no live VPN address or production credentials.

## Preconditions and diagnosis
The fictional VPN provides access to approved internal resources when a user is off campus. First verify that ordinary internet browsing works without the VPN. A failed home internet connection cannot be fixed by repeatedly reconnecting the VPN. Ask for the operating system and the exact error text. Determine whether the tunnel fails to connect or connects successfully but a particular internal application remains inaccessible.

Use the simulated service-status tool to establish the current VPN state. During a known outage, avoid advising repeated reinstallation or credential changes. Report that recovery time is unknown unless the tool provides a specific update. If general internet access works and the simulated VPN service is operational, proceed with the limited client checks below.

## Client checks
Ask the user to confirm they are using the institution-authorized client and the configuration supplied by their administrator. Never invent a server address, certificate or security setting. Close and reopen the client once, then try a normal sign-in. Check that the device date and time are correct because an incorrect clock can interfere with authentication. If authentication is rejected, refer to the account-access procedure. Never ask for passwords, recovery codes or multi-factor codes.

If the tunnel connects but one internal resource fails, ask which resource is affected, whether other approved internal resources work, and whether the same resource is accessible from an authorized campus connection. This separates a tunnel issue from an application outage or missing permission. Do not recommend disabling a firewall, certificate verification, multi-factor authentication or endpoint protection to bypass an error.

## Escalation evidence
If these checks do not resolve the problem, record the client name and version, operating system, error text, time of failure, whether internet access works, and whether other users are affected. Do not include tokens, keys or full private configuration files. A brief incident summary can be stored across sessions only with the user's permission.

Offer a simulated support ticket after the basic checks. A draft is not an existing ticket and has no service guarantee. The separate confirmation command or interface button is required to create it. Refer to the escalation policy for priority targets; those targets are training values, not actual university commitments.
