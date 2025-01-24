{ pkgs }: {
  deps = [
    pkgs.ffmpeg-full
    pkgs.ffmpeg
    pkgs.python310Full
    pkgs.python310Packages.pip
  ];
}
