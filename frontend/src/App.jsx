import React, { useState } from 'react';
import Login from './components/Login.jsx';
import SubmitClaim from './components/SubmitClaim.jsx';
import ClaimResult from './components/ClaimResult.jsx';
import ClaimHistory from './components/ClaimHistory.jsx';
import ReviewQueue from './components/ReviewQueue.jsx';

export default function App() {
  const [authToken, setAuthToken] = useState(null);
  const [userRole, setUserRole] = useState('user');
  const [currentScreen, setCurrentScreen] = useState('submit');
  const [claimResult, setClaimResult] = useState(null);

  if (!authToken) {
    return <Login authToken={authToken} setAuthToken={setAuthToken} setUserRole={setUserRole} />;
  }

  const shared = {
    authToken,
    setAuthToken,
    userRole,
    currentScreen,
    setCurrentScreen,
  };

  if (currentScreen === 'review') {
    return <ReviewQueue {...shared} />;
  }

  if (currentScreen === 'history') {
    return <ClaimHistory {...shared} setClaimResult={setClaimResult} />;
  }

  if (currentScreen === 'result') {
    return <ClaimResult {...shared} claimResult={claimResult} />;
  }

  return <SubmitClaim {...shared} setClaimResult={setClaimResult} />;
}