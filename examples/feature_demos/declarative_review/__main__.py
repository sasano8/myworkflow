"""Run the example catalog."""
import argparse
from examples.feature_demos.declarative_review.contract import compiled, documentation
from myworkflow.generation.flowcharts import render_business_flow


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--flowchart', action='store_true', help='業務フロー図だけ出力する')
args = parser.parse_args()
text = render_business_flow(compiled.graphs[0], compiled.catalog) if args.flowchart else documentation()
print(text, end='')
