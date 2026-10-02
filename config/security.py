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
