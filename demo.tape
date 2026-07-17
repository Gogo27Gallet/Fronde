# FRONDE — capture automatisée du GIF de démo (vhs, github.com/charmbracelet/vhs)
#   vhs demo.tape   → assets/demo.gif
# Terminal large, police lisible, thème sombre ; lance la démo --with-repeat et
# attend l'apparition du "Récap" (pas de Sleep fixe → pas de temps mort en fin).

Output assets/demo.gif

Set Shell "bash"
Set FontSize 22
Set Width 1320
Set Height 760
Set Padding 24
Set Theme "Dracula"
Set Framerate 10

Hide
Type "cd ~/fronde && clear"
Enter
Show

Type "python3 demo.py --with-repeat"
Enter
Wait+Screen@480s /Récap/
Sleep 5s
