from config_loader import load_config

print("🌐 loading config...")
config = load_config()
print("✅ config loaded with servers:", list(config["SERVERS"].keys()))

start_times = {}
