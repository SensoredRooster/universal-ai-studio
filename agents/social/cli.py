"""Command-line interface for the social agent."""
import argparse
import sys

from .orchestrator import SocialAgent


def main():
    parser = argparse.ArgumentParser(description="Universal AI Studio Social Agent")
    parser.add_argument("--topics", type=str, default="AI,technology", help="Comma-separated trend topics")
    parser.add_argument("--post", action="store_true", help="Upload immediately after generation")
    parser.add_argument("--scheduler", action="store_true", help="Run the scheduling loop")
    args = parser.parse_args()

    topics = [t.strip() for t in args.topics.split(",") if t.strip()]
    agent = SocialAgent()

    if args.scheduler:
        print("Starting social agent scheduler...")
        agent.run_scheduler(topics)
    else:
        try:
            result = agent.run_once(topics=topics, post=args.post)
            print(result)
        except Exception as exc:
            print(f"Failed: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
