"""
Smart Road Vision — AI-Based Intelligent Traffic Monitoring and Road Safety System
Main Application Entry Point.

Usage:
    python main.py               # Launch main desktop GUI application
    python main.py --demo        # Launch and auto-load synthetic demo traffic video
    python main.py --video path  # Launch with custom video file
    python main.py --webcam 0    # Launch with webcam feed
    python main.py --generate    # Generate sample_traffic.mp4 synthetic test video
    python main.py --test        # Run all test suites
"""

import os
import sys
import argparse
import logging
import tkinter as tk

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("SmartRoadVision")


def main():
    parser = argparse.ArgumentParser(description="Smart Road Vision - AI Intelligent Traffic Monitoring System")
    parser.add_argument("--demo", action="store_true", help="Launch GUI with synthetic traffic video demo")
    parser.add_argument("--video", type=str, default="", help="Path to video file to monitor")
    parser.add_argument("--webcam", type=int, default=None, help="Camera index to use for live monitoring")
    parser.add_argument("--generate", action="store_true", help="Generate synthetic traffic demo video and exit")
    parser.add_argument("--test", action="store_true", help="Run automated test suite and exit")
    args = parser.parse_args()

    # 1. Generate sample video if requested
    if args.generate:
        print("[Smart Road Vision] Generating synthetic traffic demonstration video...")
        from utils.generate_traffic_video import generate_sample_video
        out = generate_sample_video("sample_traffic.mp4")
        print(f"[Smart Road Vision] Demonstration video ready at: {os.path.abspath(out)}")
        return

    # 2. Run test suites if requested
    if args.test:
        print("[Smart Road Vision] Running unit tests...")
        import unittest
        suite = unittest.defaultTestLoader.discover("tests")
        runner = unittest.TextTestRunner(verbosity=2)
        res = runner.run(suite)
        sys.exit(0 if res.wasSuccessful() else 1)

    # 3. Ensure synthetic video exists for effortless viva demonstration
    if not os.path.exists("sample_traffic.mp4") and not args.video:
        try:
            logger.info("Generating demonstration video 'sample_traffic.mp4'...")
            from utils.generate_traffic_video import generate_sample_video
            generate_sample_video("sample_traffic.mp4")
        except Exception as e:
            logger.warning(f"Could not generate synthetic test video: {e}")

    # 4. Launch Tkinter GUI Application
    logger.info("Initializing Smart Road Vision Desktop Command Center...")
    try:
        from src.gui.app import SmartRoadVisionApp

        root = tk.Tk()
        app = SmartRoadVisionApp(root)

        # Handle CLI source overrides
        if args.video and os.path.exists(args.video):
            app.views["Live Monitoring"].source_var.set("file")
            app.views["Live Monitoring"].entry_source.delete(0, tk.END)
            app.views["Live Monitoring"].entry_source.insert(0, os.path.abspath(args.video))
            app.video_processor.set_source("file", os.path.abspath(args.video))
            if args.demo:
                app.start_monitoring()
        elif args.webcam is not None:
            app.views["Live Monitoring"].source_var.set("webcam")
            app.views["Live Monitoring"].entry_source.delete(0, tk.END)
            app.views["Live Monitoring"].entry_source.insert(0, str(args.webcam))
            app.video_processor.set_source("webcam", args.webcam)
            if args.demo:
                app.start_monitoring()
        elif args.demo:
            if os.path.exists("sample_traffic.mp4"):
                app.video_processor.set_source("file", os.path.abspath("sample_traffic.mp4"))
                app.start_monitoring()

        root.mainloop()

    except ImportError as e:
        logger.critical(f"Missing required dependency: {e}")
        print("\n" + "=" * 60)
        print("ERROR: Missing dependencies to launch Smart Road Vision.")
        print("Please install requirements using:")
        print("    pip install -r requirements.txt")
        print("=" * 60 + "\n")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Fatal error running Smart Road Vision: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
