# nix/package.nix
# Standalone-callable HuskyCat package derivation.
#
# Used by:
#   1. This repo's flake.nix (standalone mode)
#   2. tinyland/lab's flake.nix (monorepo mode, via callPackage)
#
# Usage from any flake:
#   huskycat = pkgs.callPackage ./nix/package.nix {
#     version = "2.1.0-${self.shortRev or "dirty"}";
#   };

{ pkgs
, lib ? pkgs.lib
, version ? "2.1.0-dev"
, src ? lib.cleanSource ./..
}:

let
  pythonEnv = pkgs.python312.withPackages (ps: with ps; [
    # Core dependencies (from pyproject.toml)
    pydantic
    pyyaml
    jsonschema
    requests
    rich
    networkx
    psutil
    click
    toml
    gitpython

    # Validation tools
    black
    mypy
    flake8
    bandit
    autoflake

    # Testing (included for nix flake check)
    pytest
    pytest-cov
    hypothesis
  ]);
in pkgs.stdenvNoCC.mkDerivation {
  pname = "huskycat";
  inherit version src;

  nativeBuildInputs = [ pkgs.makeWrapper ];
  buildInputs = [ pythonEnv ];

  installPhase = ''
    mkdir -p $out/bin $out/lib
    cp -r src/huskycat $out/lib/

    makeWrapper ${pythonEnv}/bin/python $out/bin/huskycat \
      --add-flags "-m huskycat" \
      --prefix PYTHONPATH : "$out/lib"
  '';

  passthru = {
    inherit pythonEnv;
  };

  meta = with lib; {
    description = "Universal Code Validation Platform with MCP Server Integration";
    homepage = "https://huskycat-570fbd.gitlab.io/";
    license = licenses.asl20;
    maintainers = [ ];
    platforms = platforms.unix;
  };
}
