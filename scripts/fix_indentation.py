from pathlib import Path

p = Path("license_engine.py")
content = p.read_text(encoding="utf-8")

# Fix custom keys branch
bad_custom = """        if (time.perf_counter() - t_perf_start) > 1.2:
            return False, "❌ Execution timing anomaly detected (Debugger step trap)", {}
                return True, "✅ Custom Key is valid and active!", rec"""

good_custom = """                if (time.perf_counter() - t_perf_start) > 1.2:
                    return False, "❌ Execution timing anomaly detected (Debugger step trap)", {}
                return True, "✅ Custom Key is valid and active!", rec"""

# Normalize \r\n to \n for replacement
has_crlf = "\r\n" in content
if has_crlf:
    content = content.replace("\r\n", "\n")

content = content.replace(bad_custom, good_custom)

# Fix admin history branch
bad_history = """        if (time.perf_counter() - t_perf_start) > 1.2:
            return False, "❌ Execution timing anomaly detected (Debugger step trap)", {}
                        return True, "✅ License Key is valid and active!", record"""

good_history = """                        if (time.perf_counter() - t_perf_start) > 1.2:
                            return False, "❌ Execution timing anomaly detected (Debugger step trap)", {}
                        return True, "✅ License Key is valid and active!", record"""

content = content.replace(bad_history, good_history)

if has_crlf:
    content = content.replace("\n", "\r\n")

p.write_text(content, encoding="utf-8")
print("[SUCCESS] Indentation fixed!")

