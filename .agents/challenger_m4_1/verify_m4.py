import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

def check_file(path, label):
    exists = os.path.exists(path)
    is_file = os.path.isfile(path) if exists else False
    size = os.path.getsize(path) if is_file else 0
    print(f"[{label}] Path: {path}")
    print(f"  - Exists: {exists}")
    print(f"  - Is File: {is_file}")
    print(f"  - Size (bytes): {size}")
    if is_file and size > 0:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        print(f"  - Line Count: {len(lines)}")
        print(f"  - Non-empty: TRUE")
        return True, size, len(lines)
    else:
        print(f"  - Non-empty: FALSE")
        return False, size, 0

def main():
    base_dir = r"d:\dataspeak"
    print("=== EMPIRICAL VERIFICATION CHECK 1: File Existence & Non-Emptiness ===")
    
    f1_ok, f1_sz, f1_lines = check_file(os.path.join(base_dir, "CHANGELOG.md"), "CHANGELOG.md")
    f2_ok, f2_sz, f2_lines = check_file(os.path.join(base_dir, "docs", "sessions", "README.md"), "docs/sessions/README.md")
    f3_ok, f3_sz, f3_lines = check_file(os.path.join(base_dir, "docs", "templates", "AI_TASK_TEMPLATE.md"), "docs/templates/AI_TASK_TEMPLATE.md")

    print("\n=== EMPIRICAL VERIFICATION CHECK 2: AGENTS.md Path Reference Verification ===")
    agents_path = os.path.join(base_dir, "AGENTS.md")
    agents_ok, agents_sz, agents_lines = check_file(agents_path, "AGENTS.md")
    
    if not agents_ok:
        print("ERROR: AGENTS.md missing or empty!")
        sys.exit(1)
        
    with open(agents_path, 'r', encoding='utf-8', errors='ignore') as f:
        agents_content = f.read()

    # Check 1: CHANGELOG.md in AGENTS.md
    has_changelog_ref = "CHANGELOG.md" in agents_content
    changelog_exists = os.path.exists(os.path.join(base_dir, "CHANGELOG.md"))
    print(f"1. CHANGELOG.md: Referenced in AGENTS.md = {has_changelog_ref}, Exists on disk = {changelog_exists}")

    # Check 2: docs/sessions/ in AGENTS.md
    has_sessions_ref = "docs/sessions/" in agents_content or "sessions/" in agents_content
    sessions_exists = os.path.isdir(os.path.join(base_dir, "docs", "sessions"))
    print(f"2. docs/sessions/: Referenced in AGENTS.md = {has_sessions_ref}, Dir exists on disk = {sessions_exists}")

    # Check 3: docs/templates/AI_TASK_TEMPLATE.md in AGENTS.md
    has_template_ref = "docs/templates/AI_TASK_TEMPLATE.md" in agents_content or "AI_TASK_TEMPLATE.md" in agents_content
    template_exists = os.path.exists(os.path.join(base_dir, "docs", "templates", "AI_TASK_TEMPLATE.md"))
    print(f"3. docs/templates/AI_TASK_TEMPLATE.md: Referenced in AGENTS.md = {has_template_ref}, Exists on disk = {template_exists}")

    # Check 4: proxy.js location in AGENTS.md
    proxy_root_exists = os.path.exists(os.path.join(base_dir, "proxy.js"))
    proxy_backend_exists = os.path.exists(os.path.join(base_dir, "backend", "proxy.js"))
    
    # Check tree structure representation in AGENTS.md
    lines = agents_content.splitlines()
    proxy_lines_in_agents = [line for line in lines if "proxy.js" in line]
    print(f"4. proxy.js in AGENTS.md references:")
    for pl in proxy_lines_in_agents:
        print(f"   Line: {pl}")
    print(f"   Physical location: root (d:\\dataspeak\\proxy.js) = {proxy_root_exists}, backend (d:\\dataspeak\\backend\\proxy.js) = {proxy_backend_exists}")

    # Check if AGENTS.md correctly lists proxy.js at root level rather than backend/
    proxy_in_backend_section = False
    in_backend_block = False
    for line in lines:
        if "### 3.3 Backend Layout (`backend/`)" in line:
            in_backend_block = True
        elif "### 3.4" in line or "## 4." in line:
            in_backend_block = False
        if in_backend_block and "proxy.js" in line:
            proxy_in_backend_section = True
            
    print(f"   Is proxy.js mistakenly documented inside Backend Layout (backend/)? {proxy_in_backend_section}")

    # Check if proxy.js is listed under root layout (3.1 Project Directory Structure)
    proxy_in_root_section = False
    in_root_block = False
    for line in lines:
        if "### 3.1 Project Directory Structure" in line:
            in_root_block = True
        elif "### 3.2" in line:
            in_root_block = False
        if in_root_block and "proxy.js" in line:
            proxy_in_root_section = True

    print(f"   Is proxy.js documented under Root Project Directory Structure (3.1)? {proxy_in_root_section}")

    all_pass = (
        f1_ok and f2_ok and f3_ok and
        has_changelog_ref and changelog_exists and
        has_sessions_ref and sessions_exists and
        has_template_ref and template_exists and
        proxy_root_exists and proxy_in_root_section and not proxy_in_backend_section
    )

    print("\n=== FINAL VERDICT ===")
    if all_pass:
        print("VERDICT: APPROVE")
    else:
        print("VERDICT: REJECT")

if __name__ == "__main__":
    main()
