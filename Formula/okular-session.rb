class OkularSession < Formula
  include Language::Python::Virtualenv

  desc "Save and restore Okular PDF sessions on macOS"
  homepage "https://github.com/kerata/okular-session"
  url "https://github.com/kerata/okular-session/archive/refs/tags/v0.2.0.tar.gz"
  sha256 "29409a3417141201a5cd47f1382e06201729f1d4427a7a8711421567a424e120"
  license "MIT"

  depends_on "python@3.13"

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"okular-session", "--help"
  end
end
