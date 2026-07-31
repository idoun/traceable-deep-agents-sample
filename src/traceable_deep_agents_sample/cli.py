import argparse

from traceable_deep_agents_sample.agent import run_fixture_agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Tech Radar Analyst sample")
    parser.add_argument("question")
    args = parser.parse_args()

    response = run_fixture_agent(args.question)
    print(response.answer)
    print()
    print("Sources:")
    for index, source in enumerate(response.sources, start=1):
        print(f"[{index}] {source.title} ({source.issue_date}) - {source.url}")
    print()
    print(f"run_id: {response.run_id}")
    print(f"trace_path: {response.trace_path}")


if __name__ == "__main__":
    main()

