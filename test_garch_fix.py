"""Quick test of GARCH-T fix with diagnostic plot generation."""

import numpy as np
import yfinance as yf
from qse.distributions.fitters.garch_t_fitter import GarchTFitter
from qse.distributions.fitters.laplace_fitter import LaplaceFitter
from qse.distributions.fitters.student_t_fitter import StudentTFitter
from qse.distributions.plotting.fit_diagnostics import plot_distribution_fits
from qse.distributions.distribution_audit import ModelSpec
from pathlib import Path

# Fetch AAPL data
print("Fetching AAPL data...")
ticker = yf.Ticker('AAPL')
df = ticker.history(period='2y', interval='1d')
log_returns = np.log(df['Close'] / df['Close'].shift(1)).dropna().values

print(f"Data: {len(log_returns)} returns\n")

# Fit all three distributions
print("Fitting distributions...")
garch_fitter = GarchTFitter()
laplace_fitter = LaplaceFitter()
student_fitter = StudentTFitter()

garch_result = garch_fitter.fit(log_returns)
laplace_result = laplace_fitter.fit(log_returns)
student_result = student_fitter.fit(log_returns)

print("\nGARCH-T Parameters:")
for k, v in garch_result.params.items():
    print(f"  {k}: {v:.6f}")
print(f"Scale factor: {garch_fitter._scale_factor}")
print(f"Converged: {garch_result.converged}")

# Create model specs for plotting
candidate_models = [
    ModelSpec(name="laplace", cls=laplace_fitter, config={}),
    ModelSpec(name="student_t", cls=student_fitter, config={}),
    ModelSpec(name="garch_t", cls=garch_fitter, config={}),
]

fit_results = [laplace_result, student_result, garch_result]

# Generate plot
print("\nGenerating diagnostic plot...")
output_path = Path("output/distribution_fits/aapl_fit_diagnostics.png")
fig = plot_distribution_fits(
    returns=log_returns,
    fit_results=fit_results,
    candidate_models=candidate_models,
    symbol="AAPL",
    output_path=output_path,
    show_plot=False
)

print(f"✓ Plot saved to {output_path}")
print("\nDone! Check the plot to see if GARCH-T fit improved.")
