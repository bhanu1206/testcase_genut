import sys
from extraction import gen_test

if __name__ == "__main__":
    # Check if a path is provided as a command-line argument
    if len(sys.argv) != 2:
        print("Usage: python main.py <path>")
        sys.exit(1)

    path = sys.argv[1]
    gen_test(path)