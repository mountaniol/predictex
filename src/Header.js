// Header component: displays logo and subtitle at the top
import React from "react";

const Header = () => {

  return (
    <div style={{ textAlign: "center", marginBottom: 8 }}>
      <div
        style={{
          fontSize: 36,
          fontWeight: 700,
          letterSpacing: 1,
          color: "#1a2340",
          fontFamily: "'Segoe UI', 'Roboto', 'Arial', sans-serif",
        }}
      >
        Predictex AI
      </div>
      <div
        style={{
          fontSize: 20,
          fontWeight: 400,
          color: "#3a4668",
          marginTop: 4,
          marginBottom: 32,
          letterSpacing: 0.5,
        }}
      >
        SOHO Business Evaluation
      </div>
    </div>
  );
};

export default Header;