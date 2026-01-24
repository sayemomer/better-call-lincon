import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import SignupDocPage from "@/pages/SignupDocPage";

export default function App() {
  const [page, setPage] = useState<"signupDoc" | "signin">("signupDoc");
  const [accessToken, setAccessToken] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-muted flex items-center justify-center p-6">
      <div className="w-full max-w-2xl space-y-4">
        
        {/* Top navigation */}
        <div className="flex gap-2">
          <Button
            variant={page === "signupDoc" ? "default" : "outline"}
            onClick={() => setPage("signupDoc")}
          >
            Signup via Document
          </Button>

          <Button
            variant={page === "signin" ? "default" : "outline"}
            onClick={() => setPage("signin")}
          >
            Sign in
          </Button>
        </div>

        {/* Card container */}
        <Card className="rounded-2xl shadow-sm">
          <CardHeader>
            <CardTitle>
              {page === "signupDoc" && "Signup via Passport Document"}
              {page === "signin" && "Sign in"}
            </CardTitle>
          </CardHeader>

          <CardContent>

            {/* {page === "signupDoc" && (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Upload your passport document to start signup.
                </p>
                <Button>Upload Document</Button>
              </div>
            )} */}

          {page === "signupDoc" && (
          <SignupDocPage
          onAuthed={(token) => {
          setAccessToken(token);
          setPage("dashboard");
          }}
          />
          )}

            {page === "signin" && (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Enter your email and password to sign in.
                </p>
                <Button>Sign in</Button>
              </div>
            )}

          </CardContent>
        </Card>
      </div>
    </div>
  );
}