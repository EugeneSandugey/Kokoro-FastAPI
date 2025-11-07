/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/

import React from 'react';
import './WelcomeScreen.css';

const WelcomeScreen: React.FC = () => {
  return (
    <div className="welcome-screen">
      <div className="welcome-content">
        <div className="title-container">
          <span className="welcome-icon">mic</span>
          <h2>Sales Training</h2>
        </div>
        <p>Press Play to start your training session</p>
      </div>
    </div>
  );
};

export default WelcomeScreen;
