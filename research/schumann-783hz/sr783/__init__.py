"""SR783 - reference core for the 7.83 Hz research package.

Pure Python standard library only (no third-party dependency), so every
number in the report can be regenerated on any machine with Python >= 3.9.

Modules
-------
bits       IEEE 754 / fixed-point / BCD representations (exact, rational).
synth      Signal generation at the bit level: DDS, AVR Timer1, 555, display
           frames, audio buffers, pulse harmonics, rational phase sync.
physics    Earth-ionosphere cavity, coil fields, exposure limits, sensors.
secded     Generic extended Hamming code (single-error-correct,
           double-error-detect).
prng       SplitMix64 - bit-exact deterministic random numbers.
integrity  SHA-256 manifest, root hash, SECDED-protected root, hash chain.
srml       Synthetic Schumann spectra + Lorentzian fit + ridge regression.
svgplot    Tiny deterministic SVG plotting.
wav        Bit-exact PCM WAV synthesis (isochronic / binaural / monaural).
"""

__all__ = ["bits", "synth", "physics", "secded", "prng", "integrity", "srml", "svgplot", "wav"]
__version__ = "1.0.0"
