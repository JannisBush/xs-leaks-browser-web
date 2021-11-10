import re
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--base", default="test_base.py")
parser.add_argument("--input", default="../../test_1to10.py")
parser.add_argument("--output", default="test_output.py")
args = parser.parse_args()


with open(args.input, "r") as f:
    with open(args.base, "r") as base:
        base_file = base.read()
        file = f.read()
        file = re.sub(r"(.*find_element\((.*?), (\".*?\")\).*)", r"    WebDriverWait(self.driver, 10).until(expected_conditions.presence_of_element_located((\2,\3)))\n    time.sleep(1.5)\n\1", file)
        file = re.sub(r"(def test_(\d+)\(self\):\n(.*\n)+?)(\s+\n)", r"\1    self.start_crawl(\2)\n\4", file)
        file = re.sub(r"move_to_element\(element, 0, 0\)", r"move_to_element(element)", file)
        file = re.sub(r"time.sleep\(1000\)", r"time.sleep(1.5)", file)
        file = file.split("driver.quit()\n")[1]
        file = base_file + file
        with open(args.output, "w") as f:
            f.write(file)

