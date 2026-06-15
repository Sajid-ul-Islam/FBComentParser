import streamlit as st

def render_header_animation():
    """Renders the CSS and HTML for the World Cup kicking animation with a goal post."""
    st.markdown("""
        <style>
        .main .block-container {
            padding-top: 2rem;
        }
        
        /* World Cup Football Animation */
        @keyframes kick-ball {
            0% { transform: translate(0, 0) rotate(0deg); opacity: 1; }
            15% { transform: translate(60px, -80px) rotate(180deg); }
            30% { transform: translate(120px, 0px) rotate(360deg); }
            45% { transform: translate(180px, -40px) rotate(540deg); }
            60% { transform: translate(220px, 0px) rotate(720deg); }
            75% { transform: translate(250px, -15px) rotate(900deg); opacity: 1; }
            90% { transform: translate(270px, 0px) rotate(1080deg); opacity: 0; }
            100% { transform: translate(0, 0) rotate(0deg); opacity: 0; }
        }
        @keyframes kick-leg {
            0% { transform: scaleX(-1) rotate(0deg); }
            5% { transform: scaleX(-1) rotate(-20deg); }
            15% { transform: scaleX(-1) rotate(40deg); }
            30% { transform: scaleX(-1) rotate(0deg); }
            100% { transform: scaleX(-1) rotate(0deg); }
        }
        .anim-container {
            display: flex;
            align-items: flex-end;
            margin-bottom: -10px;
            white-space: nowrap;
            padding-top: 60px; /* Room for the bounce */
            position: relative;
            width: 400px;
        }
        .player {
            font-size: 75px;
            line-height: 1;
            animation: kick-leg 3s infinite;
            transform-origin: bottom center;
            z-index: 2;
        }
        .ball {
            font-size: 30px;
            line-height: 1;
            animation: kick-ball 3s infinite cubic-bezier(0.25, 0.46, 0.45, 0.94);
            margin-left: -10px;
            margin-bottom: 15px; /* Raised to foot level */
            z-index: 1;
        }
        .goal {
            font-size: 90px;
            line-height: 1;
            position: absolute;
            left: 310px;
            bottom: -5px;
            z-index: 0;
        }
        </style>
        
        <div class="anim-container">
            <div class="player">🏃‍♂️</div>
            <div class="ball">⚽</div>
            <div class="goal">🥅</div>
        </div>
    """, unsafe_allow_html=True)
