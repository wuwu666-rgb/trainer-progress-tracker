"""Local launcher, with vendored dependencies for offline classroom demos."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'vendor'))
from app import create_app

if __name__=='__main__':
    app=create_app()
    if '--demo' in sys.argv:
        from seed_demo import seed
        seed(app)
    port=int(os.environ.get('PORT','5055'))
    print(f'Repbook is ready: http://127.0.0.1:{port}')
    app.run(host='127.0.0.1',port=port,debug=False)
