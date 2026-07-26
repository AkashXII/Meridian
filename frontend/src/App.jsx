import React, { useState } from 'react';
import Login from './components/Login.jsx';
import SubmitClaim from './components/SubmitClaim.jsx';
import ClaimResult from './components/ClaimResult.jsx';
import ClaimHistory from './components/ClaimHistory.jsx';

export default function App() {
  const [authToken, setAuthToken] = useState(null);
  const [currentScreen, setCurrentScreen] = useState('submit');
  const [claimResult, setClaimResult] = useState(null);

  if (!authToken) {
    return <Login authToken={authToken} setAuthToken={setAuthToken} />;
  }

  if (currentScreen === 'history') {
    return (
      <ClaimHistory
        authToken={authToken}
        setAuthToken={setAuthToken}
        currentScreen={currentScreen}
        setCurrentScreen={setCurrentScreen}
        setClaimResult={setClaimResult}
      />
    );
  }

  if (currentScreen === 'result') {
    return (
      <ClaimResult
        authToken={authToken}
        setAuthToken={setAuthToken}
        currentScreen={currentScreen}
        setCurrentScreen={setCurrentScreen}
        claimResult={claimResult}
      />
    );
  }

  return (
    <SubmitClaim
      authToken={authToken}
      setAuthToken={setAuthToken}
      currentScreen={currentScreen}
      setCurrentScreen={setCurrentScreen}
      setClaimResult={setClaimResult}
    />
  );
}