import sys
from pathlib import Path

# Thêm thư mục gốc vào sys.path để import các module của hệ thống
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from run_clean_v19_multimetric_frontier import (
    CandidateSpec, 
    build_clean_anchors, 
    apply_candidate, 
    build_daily_panel, 
    load_sales,
    write_submission
)

def main():
    print("==================================================")
    print("      REPLICATE FINAL SUBMISSION (CLEAN V19)      ")
    print("==================================================")
    
    replicate_dir = Path(__file__).resolve().parent
    run_dir = root_dir / "logs" / "offline_public_v2"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n1. Loading base data and setting up Panel...")
    daily = build_daily_panel()
    sales = load_sales()
    
    print("\n2. Building Anchor Model (Load or Train CatBoost)...")
    anchors = build_clean_anchors(run_dir, daily, sales)
    
    print("\n3. Applying Post-processing (a=0.16, month-smooth)...")
    # Define the single chosen candidate spec
    spec = CandidateSpec(
        name="final_submission",
        family="ratio_smooth",
        scopes=("2023H2",),
        targets=("COGS",),
        alpha=0.16,
        profile="recent_even",
        preserve="month",
        note="Replicate script configuration"
    )
    
    frame = apply_candidate(anchors, daily, spec)
    
    print("\n4. Saving submission file...")
    output_path = replicate_dir / "final_submission.csv"
    write_submission(frame, output_path)
    
    print(f"\n[SUCCESS] Final submission created at: {output_path}")
    print("==================================================")

if __name__ == "__main__":
    main()
