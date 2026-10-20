<xsl:stylesheet xmlns:edirom="http://www.edirom.de/ns/1.3" xmlns="http://www.edirom.de/ns/1.3" xmlns:xi="http://www.w3.org/2001/XInclude" xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" exclude-result-prefixes="xs" version="1.0">

  <xsl:output indent="yes"/>
  <xsl:param name="editionId" select="''"/>
  <xsl:param name="editionName" select="''"/>
  <xsl:param name="editionPrefsPath" select="''"/>
  <xsl:param name="editionWorksPath" select="''"/>

  <xsl:template match="edirom:edition">
    <edition xmlns="http://www.edirom.de/ns/1.3">
      <xsl:attribute name="xml:id">
        <xsl:value-of select="$editionId"/>
      </xsl:attribute>
      <xsl:apply-templates select="@*[name() != 'xml:id'] | node()"/>
    </edition>
  </xsl:template>
  
  <xsl:template match="edirom:editionName">
    <editionName>
      <xsl:value-of select="$editionName" />
    </editionName>
  </xsl:template>

  <xsl:template match="edirom:works">
    <works>
      <xsl:copy-of select="document($editionWorksPath)/edirom:works/*"/>
    </works>
  </xsl:template>

  <xsl:template match="edirom:preferences">
    <preferences
      xlink:href="{concat('xmldb:exist:///db/apps/edirom-content/', $editionPrefsPath, '/prefs.xml')}"
    />
  </xsl:template>

  <xsl:template match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates select="@* | node()"/>
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>
