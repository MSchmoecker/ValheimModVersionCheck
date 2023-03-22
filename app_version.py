from packaging import version

with open("VERSION", 'r') as f:
    app_version = version.parse(f.read().strip())
