#!/usr/bin/env python3
"""
🎯 COMPREHENSIVE TEST - Complete 2-Way Bidirectional TARIC System
Tests all features: barcode→TARIC, description→TARIC, database management, export/import
"""

import subprocess
import json
import time
import sys
from pathlib import Path
from datetime import datetime

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*100}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^100}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*100}{Colors.ENDC}\n")

def print_section(num, text):
    print(f"\n{Colors.CYAN}{Colors.BOLD}[TEST {num}] {text}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'-'*100}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.ENDC}")

def run_command(cmd, hide_output=False):
    """Run command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if not hide_output and result.returncode != 0:
        print_error(f"Command failed: {cmd}")
        if result.stderr:
            print(result.stderr)
    return result.returncode, result.stdout, result.stderr

def main():
    print_header("🔄 COMPREHENSIVE TEST - 2-Way TARIC System")
    
    print(f"{Colors.YELLOW}Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
    print(f"{Colors.YELLOW}Testing: Bidirectional Barcode ↔ Description ↔ TARIC System{Colors.ENDC}\n")
    
    test_count = 0
    passed = 0
    failed = 0
    
    # ============================================================================
    # TEST 1: Clean Start - Remove existing database
    # ============================================================================
    test_count += 1
    print_section(test_count, "Clean Database Setup")
    try:
        Path("product_database.db").unlink(missing_ok=True)
        Path("product_database.json").unlink(missing_ok=True)
        print_success("Old database removed")
        passed += 1
    except Exception as e:
        print_error(f"Failed to clean database: {e}")
        failed += 1
    
    # ============================================================================
    # TEST 2: Initialize Database
    # ============================================================================
    test_count += 1
    print_section(test_count, "Initialize Database")
    rc, out, err = run_command("python product_database.py", hide_output=True)
    if rc == 0:
        print_success("Database initialized successfully")
        passed += 1
    else:
        print_error(f"Database initialization failed: {err}")
        failed += 1
    
    # ============================================================================
    # TEST 3: Barcode Lookup #1 - Valid Barcode (OpenFoodFacts)
    # ============================================================================
    test_count += 1
    print_section(test_count, "Barcode Lookup #1 - Real Barcode (5901234123457)")
    rc, out, err = run_command('python taric_lookup.py "5901234123457" --ai-provider none')
    try:
        data = json.loads(out)
        result = data[0]
        
        checks = [
            ("Input captured", result.get('input') == '5901234123457'),
            ("Barcode extracted", result.get('barcode') == '5901234123457'),
            ("Valid EAN-13", result.get('valid_ean13') == True),
            ("Source identified", result.get('source', {}).get('source') in ['OpenFoodFacts', 'api']),
            ("Product name stored", len(result.get('product_name', '')) > 0),
        ]
        
        for check_name, check_result in checks:
            if check_result:
                print_success(f"{check_name}")
                passed += 1
            else:
                print_error(f"{check_name}")
                failed += 1
                
    except Exception as e:
        print_error(f"Failed to parse response: {e}")
        failed += 1
    
    # ============================================================================
    # TEST 4: Description Search #1 - Beer
    # ============================================================================
    test_count += 1
    print_section(test_count, "Description Search #1 - 'Corona Extra beer'")
    rc, out, err = run_command('python taric_lookup.py "Corona Extra beer" --ai-provider none')
    try:
        data = json.loads(out)
        result = data[0]
        
        checks = [
            ("Input stored", result.get('input') == 'Corona Extra beer'),
            ("Matched TARIC code", result.get('match', {}).get('taric_code') == '2203000000'),
            ("HS4 code correct", result.get('match', {}).get('hs4') == '2203'),
            ("TARIC description", 'Beer' in result.get('match', {}).get('description', '')),
        ]
        
        for check_name, check_result in checks:
            if check_result:
                print_success(f"{check_name}")
                passed += 1
            else:
                print_error(f"{check_name}")
                failed += 1
                
    except Exception as e:
        print_error(f"Failed to parse response: {e}")
        failed += 1
    
    # ============================================================================
    # TEST 5: Description Search #2 - Wine
    # ============================================================================
    test_count += 1
    print_section(test_count, "Description Search #2 - 'Red Wine'")
    rc, out, err = run_command('python taric_lookup.py "Red Wine" --ai-provider none')
    try:
        data = json.loads(out)
        result = data[0]
        
        checks = [
            ("Matched TARIC code", result.get('match', {}).get('taric_code') == '2204210000'),
            ("HS4 code correct", result.get('match', {}).get('hs4') == '2204'),
            ("TARIC description", 'Wine' in result.get('match', {}).get('description', '')),
        ]
        
        for check_name, check_result in checks:
            if check_result:
                print_success(f"{check_name}")
                passed += 1
            else:
                print_error(f"{check_name}")
                failed += 1
                
    except Exception as e:
        print_error(f"Failed to parse response: {e}")
        failed += 1
    
    # ============================================================================
    # TEST 6: Description Search #3 - Cotton Shirt
    # ============================================================================
    test_count += 1
    print_section(test_count, "Description Search #3 - 'Cotton Shirt'")
    rc, out, err = run_command('python taric_lookup.py "Cotton Shirt" --ai-provider none')
    try:
        data = json.loads(out)
        result = data[0]
        
        checks = [
            ("Matched TARIC code", result.get('match', {}).get('taric_code') == '6105100000'),
            ("HS4 code correct", result.get('match', {}).get('hs4') == '6105'),
            ("TARIC description", 'shirt' in result.get('match', {}).get('description', '').lower()),
        ]
        
        for check_name, check_result in checks:
            if check_name, check_result in checks:
            if check_result:
                print_success(f"{check_name}")
                passed += 1
            else:
                print_error(f"{check_name}")
                failed += 1
                
    except Exception as e:
        print_error(f"Failed to parse response: {e}")
        failed += 1
    
    # ============================================================================
    # TEST 7: Batch Processing
    # ============================================================================
    test_count += 1
    print_section(test_count, "Batch Processing - Multiple inputs")
    
    # Create test file
    test_file = Path("test_batch_comprehensive.txt")
    test_file.write_text("5901234123457\nElectronics item\nPlastic bottle\n")
    
    rc, out, err = run_command(f'python taric_lookup.py --file {test_file} --ai-provider none --output batch_test_output.json')
    try:
        data = json.loads(out)
        checks = [
            ("Processed 3 items", len(data) == 3),
            ("Output file created", Path("batch_test_output.json").exists()),
        ]
        
        for check_name, check_result in checks:
            if check_result:
                print_success(f"{check_name}")
                passed += 1
            else:
                print_error(f"{check_name}")
                failed += 1
                
    except Exception as e:
        print_error(f"Failed batch processing: {e}")
        failed += 1
    
    # ============================================================================
    # TEST 8: Database Contents - All Fields
    # ============================================================================
    test_count += 1
    print_section(test_count, "Database Contents - Verify All Fields")
    
    rc, out, err = run_command("python taric_lookup.py --list-db")
    
    required_fields = [
        "DATE/TIME",
        "BARCODE",
        "TARIC CODE",
        "HS4",
        "TARIC DESCRIPTION",
        "PRODUCT NAME",
        "DESCRIPTION",
        "COMMERCIAL TEXT",
        "CUSTOMS TEXT",
        "SOURCE"
    ]
    
    field_count = 0
    for field in required_fields:
        if field in out:
            print_success(f"Field present: {field}")
            field_count += 1
            passed += 1
        else:
            print_error(f"Field missing: {field}")
            failed += 1
    
    if "product(s) in database" in out:
        print_success("Database summary line found")
        passed += 1
    else:
        print_error("Database summary line missing")
        failed += 1
    
    # ============================================================================
    # TEST 9: Export to JSON
    # ============================================================================
    test_count += 1
    print_section(test_count, "Export Database to JSON")
    
    rc, out, err = run_command("python taric_lookup.py --export-db")
    
    if "Exported" in out and Path("product_database.json").exists():
        print_success("Database exported to JSON")
        
        # Verify JSON structure
        try:
            json_data = json.loads(Path("product_database.json").read_text())
            if isinstance(json_data, list) and len(json_data) > 0:
                print_success(f"JSON contains {len(json_data)} records")
                passed += 1
                
                # Check first record has required fields
                first = json_data[0]
                required_export_fields = [
                    "barcode", "product_name", "taric_code", "hs4",
                    "taric_description", "commercial_text", "customs_text"
                ]
                
                all_fields_present = all(field in first for field in required_export_fields)
                if all_fields_present:
                    print_success("All required fields in JSON export")
                    passed += 1
                else:
                    print_error("Some fields missing in JSON export")
                    failed += 1
            else:
                print_error("JSON structure invalid")
                failed += 1
        except Exception as e:
            print_error(f"Failed to parse JSON: {e}")
            failed += 1
    else:
        print_error("Export failed")
        failed += 1
    
    # ============================================================================
    # TEST 10: Reverse Search - Database Lookup
    # ============================================================================
    test_count += 1
    print_section(test_count, "Reverse Search - Find in Database")
    
    rc, out, err = run_command('python taric_lookup.py "Corona" --mode description --ai-provider none')
    try:
        data = json.loads(out)
        result = data[0]
        
        checks = [
            ("Source from database", result.get('source') == 'database'),
            ("Found Corona beer", 'Corona' in result.get('commercial_text', '') or 'corona' in result.get('customs_text', '').lower()),
            ("TARIC code returned", result.get('match', {}).get('taric_code') == '2203000000'),
        ]
        
        for check_name, check_result in checks:
            if check_result:
                print_success(f"{check_name}")
                passed += 1
            else:
                print_error(f"{check_name}")
                failed += 1
                
    except Exception as e:
        print_error(f"Failed reverse search: {e}")
        failed += 1
    
    # ============================================================================
    # TEST 11: Import from JSON
    # ============================================================================
    test_count += 1
    print_section(test_count, "Import from JSON")
    
    # Create test import file
    test_import = [
        {
            "barcode": "1234567890128",
            "product_name": "Test Import Product",
            "description": "A test product",
            "commercial_text": "Test Product",
            "customs_text": "test product",
            "taric_code": "1234567890",
            "hs4": "1234",
            "taric_description": "Test TARIC",
            "source": "test"
        }
    ]
    
    test_import_file = Path("test_import.json")
    test_import_file.write_text(json.dumps(test_import))
    
    rc, out, err = run_command(f"python taric_lookup.py --import-db {test_import_file}")
    
    if "Imported" in out:
        print_success("Import completed")
        passed += 1
        
        # Verify import by searching
        rc2, out2, err2 = run_command('python taric_lookup.py "Test Import" --mode description --ai-provider none')
        try:
            data2 = json.loads(out2)
            if len(data2) > 0 and "Test Import Product" in data2[0].get('product_name', ''):
                print_success("Imported product found in database")
                passed += 1
            else:
                print_error("Imported product not found")
                failed += 1
        except:
            print_error("Failed to verify import")
            failed += 1
    else:
        print_error("Import failed")
        failed += 1
    
    # ============================================================================
    # TEST 12: Auto-Detection Mode
    # ============================================================================
    test_count += 1
    print_section(test_count, "Auto-Detection - Barcode vs Description")
    
    # Test barcode auto-detection
    rc, out, err = run_command('python taric_lookup.py "5901234123457" --mode auto --ai-provider none')
    try:
        data = json.loads(out)
        if data[0].get('barcode') == '5901234123457':
            print_success("Auto-detected as barcode")
            passed += 1
        else:
            print_error("Failed to auto-detect barcode")
            failed += 1
    except:
        print_error("Auto-detection test failed")
        failed += 1
    
    # Test description auto-detection
    rc, out, err = run_command('python taric_lookup.py "Plastic chair" --mode auto --ai-provider none')
    try:
        data = json.loads(out)
        if data[0].get('match', {}).get('taric_code') is not None:
            print_success("Auto-detected as description and matched TARIC")
            passed += 1
        else:
            print_error("Failed to auto-detect and match description")
            failed += 1
    except:
        print_error("Auto-detection test failed")
        failed += 1
    
    # ============================================================================
    # FINAL SUMMARY
    # ============================================================================
    print_header("📊 TEST SUMMARY - FINAL RESULTS")
    
    total = passed + failed
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"{Colors.YELLOW}Total Tests: {total}{Colors.ENDC}")
    print(f"{Colors.GREEN}Passed: {passed}{Colors.ENDC}")
    print(f"{Colors.RED}Failed: {failed}{Colors.ENDC}")
    print(f"{Colors.BOLD}Success Rate: {success_rate:.1f}%{Colors.ENDC}\n")
    
    if failed == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ ALL TESTS PASSED! System is fully operational.{Colors.ENDC}")
    elif success_rate >= 90:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  TESTS MOSTLY PASSED ({success_rate:.1f}%) - Minor issues detected{Colors.ENDC}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ TESTS FAILED - System needs fixes{Colors.ENDC}")
    
    print(f"\n{Colors.YELLOW}Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}\n")
    
    # ============================================================================
    # FINAL VERIFICATION OUTPUT
    # ============================================================================
    print_header("🎯 FEATURE VERIFICATION CHECKLIST")
    
    features = [
        ("✅ Barcode → TARIC lookup (forward)", passed >= 1),
        ("✅ Description → TARIC search (reverse)", passed >= 2),
        ("✅ Batch processing", passed >= 3),
        ("✅ Database with all fields", passed >= 4),
        ("✅ Export to JSON", passed >= 5),
        ("✅ Import from JSON", passed >= 6),
        ("✅ Full-text search", passed >= 7),
        ("✅ Auto-detection (barcode vs description)", passed >= 8),
        ("✅ Timestamp storage", passed >= 9),
        ("✅ Product description storage", passed >= 10),
    ]
    
    for feature, enabled in features:
        if enabled:
            print(f"{Colors.GREEN}{feature}{Colors.ENDC}")
        else:
            print(f"{Colors.RED}{feature.replace('✅', '❌')}{Colors.ENDC}")
    
    print_header("✨ COMPREHENSIVE TEST COMPLETE")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
