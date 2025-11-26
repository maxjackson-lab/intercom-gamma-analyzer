import sys
import os
import importlib
import pkgutil
import traceback

# Add project root to path
sys.path.append(os.getcwd())

def check_imports(package_name):
    print(f"Checking imports for package: {package_name}")
    package = importlib.import_module(package_name)
    
    results = []
    
    if hasattr(package, "__path__"):
        for _, name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            try:
                importlib.import_module(name)
                results.append((name, "OK", ""))
            except Exception as e:
                results.append((name, "FAILED", traceback.format_exc()))
    
    return results

print("Starting import check...")
agents_results = check_imports("src.agents")
services_results = check_imports("src.services")

print("\n--- Import Check Results ---")
failed_count = 0
for name, status, error in agents_results + services_results:
    if status == "FAILED":
        print(f"❌ {name}: {status}")
        print(f"Error details:\n{error}\n")
        failed_count += 1
    else:
        # print(f"✅ {name}: {status}") # Reduce noise
        pass

if failed_count == 0:
    print("\n✅ All modules imported successfully.")
else:
    print(f"\n❌ {failed_count} modules failed to import.")
    sys.exit(1)
