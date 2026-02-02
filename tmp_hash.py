import hashlib, json
payload='"'"'{"foo":"bar"}'"'"'
canonical=json.dumps(json.loads(payload), sort_keys=True, separators=(',',':'))
print(canonical)
print(hashlib.sha256(canonical.encode()).hexdigest())
