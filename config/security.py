import ipaddress


def parse_trusted_proxies(entries):
    """Parse configured trusted proxy IPs or CIDRs into network objects."""
    if not entries:
        return ()
    if isinstance(entries, str):
        raw_items = [item.strip() for item in entries.split(',') if item.strip()]
    else:
        raw_items = [str(item).strip() for item in entries if str(item).strip()]
    networks = []
    for item in raw_items:
        networks.append(ipaddress.ip_network(item, strict=False))
    return tuple(networks)


def _ip_in_networks(address, networks):
    return any(address.version == network.version and address in network for network in networks)


def validated_client_ip(request, trusted_proxies=None, trust_render_client_ip=False):
    """Extract the client IP, trusting X-Forwarded-For only from configured proxies."""
    meta = getattr(request, 'META', None) or {}
    if trust_render_client_ip:
        # Render public web traffic reaches the container through its managed
        # edge, which overwrites CF-Connecting-IP. This mode is explicit so a
        # self-hosted deployment never trusts a caller-supplied header by
        # accident.
        raw_render_client = str(meta.get('HTTP_CF_CONNECTING_IP', '') or '').strip()
        try:
            return str(ipaddress.ip_address(raw_render_client))
        except ValueError:
            pass
    raw_remote = str(meta.get('REMOTE_ADDR', '') or '').strip()
    try:
        remote_ip = ipaddress.ip_address(raw_remote)
    except ValueError:
        return 'unknown'
    try:
        networks = parse_trusted_proxies(trusted_proxies)
    except ValueError:
        networks = ()
    if not networks or not _ip_in_networks(remote_ip, networks):
        return str(remote_ip)
    forwarded_for = str(meta.get('HTTP_X_FORWARDED_FOR', '') or '').strip()
    if not forwarded_for:
        return str(remote_ip)
    fallback = str(remote_ip)
    for raw_hop in reversed(forwarded_for.split(',')):
        hop = raw_hop.strip()
        if not hop:
            return fallback
        try:
            hop_ip = ipaddress.ip_address(hop)
        except ValueError:
            return fallback
        if _ip_in_networks(hop_ip, networks):
            fallback = str(hop_ip)
            continue
        return str(hop_ip)
    return fallback


def trusted_csrf_origins(origin, allowed_hosts, render_hostname):
    """Trust the canonical HTTPS origin and this service's allowed Render alias.

    Render terminates TLS, so Django may see an HTTP request even when the
    browser sends an HTTPS Origin. Both public entry points need exact origins.
    """
    origins = [origin] if origin.startswith('https://') else []
    if (render_hostname and render_hostname in allowed_hosts
            and '*' not in render_hostname and '/' not in render_hostname):
        alias = f'https://{render_hostname}'
        if alias not in origins:
            origins.append(alias)
    return origins
